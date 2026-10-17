import datetime
from django.utils import timezone
from django.db import transaction
from django.db.models import Q
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import (
    Club,
    ClubMember,
    ClubTournament,
    ClubMatch,
    LiveMatchTimerState,
    LiveCricketScorecard
)
from .serializers import (
    ClubSerializer,
    ClubMemberSerializer,
    ClubTournamentSerializer,
    ClubMatchSerializer,
    LiveMatchTimerStateSerializer,
    LiveCricketScorecardSerializer
)
from sports.models import Team, Player, Sport
from accounts.models import User

class IsClubAdminOrOwner(permissions.BasePermission):
    """
    Allows access if the user is the club Owner, Co-Owner, or Co-Administrator.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        club = getattr(obj, 'club', obj) if not isinstance(obj, Club) else obj
        if club.owner == request.user:
            return True
        member = club.members.filter(user=request.user, is_active=True).first()
        return member and member.role in ['OWNER', 'CO_OWNER', 'CO_ADMIN']


class ClubViewSet(viewsets.ModelViewSet):
    queryset = Club.objects.all().prefetch_related('members', 'tournaments', 'matches')
    serializer_class = ClubSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        qs = Club.objects.all()
        user = self.request.user
        mine = self.request.query_params.get('mine')
        if mine == 'true' and user.is_authenticated:
            qs = qs.filter(Q(owner=user) | Q(members__user=user)).distinct()
        elif not user.is_authenticated:
            qs = qs.filter(privacy='PUBLIC')
        return qs

    def perform_create(self, serializer):
        club = serializer.save(owner=self.request.user)
        # Automatically make creator the Owner in ClubMember
        ClubMember.objects.create(
            club=club,
            user=self.request.user,
            role='OWNER',
            is_active=True
        )

        # Check if co-owner / co-admin was provided during club creation
        co_admin_email = self.request.data.get('co_admin_email', '').strip()
        co_admin_role = self.request.data.get('co_admin_role', 'CO_ADMIN')
        if co_admin_email:
            target_user = User.objects.filter(
                Q(email__iexact=co_admin_email) | Q(username__iexact=co_admin_email)
            ).first()
            if target_user and target_user != self.request.user:
                assigned_role = co_admin_role if co_admin_role in ['CO_OWNER', 'CO_ADMIN'] else 'CO_ADMIN'
                ClubMember.objects.create(
                    club=club,
                    user=target_user,
                    role=assigned_role,
                    is_active=True
                )

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def add_member(self, request, pk=None):
        club = self.get_object()
        # Only Owner or Co-Owner can add/manage administrators
        caller_member = club.members.filter(user=request.user, is_active=True).first()
        is_owner = (club.owner == request.user) or (caller_member and caller_member.role == 'CO_OWNER')
        
        if not is_owner:
            return Response({'error': 'Only club owner or co-owners can add and assign club staff.'}, status=status.HTTP_403_FORBIDDEN)

        user_id = request.data.get('user_id')
        email = request.data.get('email')
        role = request.data.get('role', 'MEMBER')

        if role not in ['CO_OWNER', 'CO_ADMIN', 'SCORER', 'MEMBER']:
            return Response({'error': 'Invalid role specified.'}, status=status.HTTP_400_BAD_REQUEST)

        target_user = None
        if user_id:
            target_user = User.objects.filter(id=user_id).first()
        elif email:
            target_user = User.objects.filter(email=email).first()

        if not target_user:
            return Response({'error': 'Target user not found.'}, status=status.HTTP_404_NOT_FOUND)

        member, created = ClubMember.objects.get_or_create(
            club=club,
            user=target_user,
            defaults={'role': role, 'is_active': True}
        )
        if not created:
            member.role = role
            member.is_active = True
            member.save()

        return Response(ClubMemberSerializer(member).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def remove_member(self, request, pk=None):
        club = self.get_object()
        if club.owner != request.user:
            caller_member = club.members.filter(user=request.user, is_active=True).first()
            if not caller_member or caller_member.role != 'CO_OWNER':
                return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

        user_id = request.data.get('user_id')
        member = club.members.filter(user_id=user_id).first()
        if not member:
            return Response({'error': 'Member not found.'}, status=status.HTTP_404_NOT_FOUND)
        if member.user == club.owner:
            return Response({'error': 'Cannot remove the primary club owner.'}, status=status.HTTP_400_BAD_REQUEST)

        member.delete()
        return Response({'message': 'Member removed successfully.'})

    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def join_by_invite(self, request):
        code = request.data.get('invite_code', '').strip().upper()
        if not code:
            return Response({'error': 'Invite code is required.'}, status=status.HTTP_400_BAD_REQUEST)

        club = Club.objects.filter(invite_code=code).first()
        if not club:
            return Response({'error': 'Invalid invite code.'}, status=status.HTTP_404_NOT_FOUND)

        member, created = ClubMember.objects.get_or_create(
            club=club,
            user=request.user,
            defaults={'role': 'MEMBER', 'is_active': True}
        )
        return Response(ClubSerializer(club, context={'request': request}).data)


class ClubTournamentViewSet(viewsets.ModelViewSet):
    serializer_class = ClubTournamentSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        club_id = self.request.query_params.get('club_id')
        if club_id:
            return ClubTournament.objects.filter(club_id=club_id).order_by('-created_at')
        return ClubTournament.objects.all().order_by('-created_at')

    def perform_create(self, serializer):
        club_id = self.request.data.get('club')
        club = Club.objects.get(id=club_id)
        # Check permissions: owner, co_owner, co_admin
        if club.owner != self.request.user:
            member = club.members.filter(user=self.request.user, is_active=True).first()
            if not member or member.role not in ['CO_OWNER', 'CO_ADMIN']:
                raise permissions.exceptions.PermissionDenied("You do not have permission to create tournaments in this club.")
        serializer.save()


class ClubMatchViewSet(viewsets.ModelViewSet):
    serializer_class = ClubMatchSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        qs = ClubMatch.objects.all().select_related('club', 'team1', 'team2', 'turf', 'court', 'tournament', 'timer_state', 'scorecard')
        club_id = self.request.query_params.get('club_id')
        if club_id:
            qs = qs.filter(club_id=club_id)
        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param)
        return qs.order_by('-match_date')

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        
        # Resolve team1 either from UUID or by name
        team1_val = data.get('team1')
        if team1_val:
            team1_obj = None
            try:
                team1_obj = Team.objects.filter(id=team1_val).first()
            except Exception:
                team1_obj = None
            if not team1_obj:
                team1_obj = Team.objects.filter(name__iexact=str(team1_val).strip()).first()
            if not team1_obj:
                cricket_sport = Sport.objects.filter(name__icontains='Cricket').first() or Sport.objects.first()
                team1_obj, _ = Team.objects.get_or_create(
                    name=str(team1_val).strip(),
                    defaults={'user': request.user, 'sport': cricket_sport}
                )
            data['team1'] = str(team1_obj.id)

        # Resolve team2 either from UUID or by name
        team2_val = data.get('team2')
        if team2_val:
            team2_obj = None
            try:
                team2_obj = Team.objects.filter(id=team2_val).first()
            except Exception:
                team2_obj = None
            if not team2_obj:
                team2_obj = Team.objects.filter(name__iexact=str(team2_val).strip()).first()
            if not team2_obj:
                cricket_sport = Sport.objects.filter(name__icontains='Cricket').first() or Sport.objects.first()
                team2_obj, _ = Team.objects.get_or_create(
                    name=str(team2_val).strip(),
                    defaults={'user': request.user, 'sport': cricket_sport}
                )
            data['team2'] = str(team2_obj.id)

        # Capture ball_type and ground_name inside custom_rules
        custom_rules = data.get('custom_rules') or {}
        if isinstance(custom_rules, str):
            import json
            try:
                custom_rules = json.loads(custom_rules)
            except Exception:
                custom_rules = {}
        if 'ball_type' in data:
            custom_rules['ball_type'] = data['ball_type']
        if 'ground_name' in data:
            custom_rules['ground_name'] = data['ground_name']
        if 'total_overs' in data:
            try:
                custom_rules['total_overs'] = int(data['total_overs'])
            except Exception:
                pass
        if 'venue_type' in data:
            custom_rules['venue_type'] = data['venue_type']
        data['custom_rules'] = custom_rules

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        club = serializer.validated_data.get('club')
        # Check permissions: owner, co_owner, co_admin
        if club.owner != self.request.user:
            member = club.members.filter(user=self.request.user, is_active=True).first()
            if not member or member.role not in ['CO_OWNER', 'CO_ADMIN']:
                raise permissions.exceptions.PermissionDenied("You do not have permission to create matches in this club.")
        
        # Calculate wickets allowed dynamically if not explicitly provided
        team1_players = serializer.validated_data.get('team1_players_count', 7)
        wickets = serializer.validated_data.get('wickets_allowed')
        if not wickets:
            wickets = max(1, team1_players - 1)
            serializer.validated_data['wickets_allowed'] = wickets

        match = serializer.save()

        # Initialize Timer and Scorecard with custom or club defaults
        default_inning_minutes = self.request.data.get('inning_minutes') or club.customization.get('default_inning_minutes', 13)
        default_reminder = self.request.data.get('reminder_seconds') or club.customization.get('default_reminder_seconds', 120)
        
        LiveMatchTimerState.objects.create(
            match=match,
            inning_duration_seconds=int(default_inning_minutes) * 60,
            reminder_threshold_seconds=int(default_reminder)
        )
        LiveCricketScorecard.objects.create(
            match=match,
            batting_team=match.team1,
            bowling_team=match.team2
        )

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def start_match_day(self, request, pk=None):
        """Pre-match initialization: sets status to TOSS or configures initial inning time"""
        match = self.get_object()
        timer, _ = LiveMatchTimerState.objects.get_or_create(match=match)
        scorecard, _ = LiveCricketScorecard.objects.get_or_create(match=match)

        # Allow dynamic inning time and reminder config
        inning_minutes = request.data.get('inning_minutes')
        reminder_seconds = request.data.get('reminder_seconds')
        if inning_minutes:
            timer.inning_duration_seconds = int(inning_minutes) * 60
        if reminder_seconds:
            timer.reminder_threshold_seconds = int(reminder_seconds)
        timer.save()

        if match.status == 'SCHEDULED':
            match.status = 'TOSS'
            match.save()

        return Response(ClubMatchSerializer(match, context={'request': request}).data)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def record_toss(self, request, pk=None):
        """Records who won the toss (Team A / Team B) and decision (Batting / Bowling)"""
        match = self.get_object()
        toss_winner_id = request.data.get('toss_winner_id')
        decision = request.data.get('toss_decision', 'BAT').upper()

        if decision not in ['BAT', 'BOWL']:
            return Response({'error': 'Invalid toss decision. Choose BAT or BOWL.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            toss_winner = Team.objects.get(id=toss_winner_id)
        except Team.DoesNotExist:
            return Response({'error': 'Toss winner team not found.'}, status=status.HTTP_404_NOT_FOUND)

        match.toss_winner = toss_winner
        match.toss_decision = decision
        match.status = 'IN_PROGRESS'
        match.save()

        # Designate Batting & Bowling Teams
        scorecard, _ = LiveCricketScorecard.objects.get_or_create(match=match)
        other_team = match.team2 if toss_winner == match.team1 else match.team1

        if decision == 'BAT':
            scorecard.batting_team = toss_winner
            scorecard.bowling_team = other_team
        else:
            scorecard.batting_team = other_team
            scorecard.bowling_team = toss_winner
        scorecard.save()

        # Start Inning Timer automatically upon toss completion if requested
        auto_start_timer = request.data.get('auto_start_timer', True)
        if auto_start_timer:
            timer, _ = LiveMatchTimerState.objects.get_or_create(match=match)
            timer.is_running = True
            timer.is_paused = False
            timer.last_resumed_at = timezone.now()
            timer.save()

        return Response(ClubMatchSerializer(match, context={'request': request}).data)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def timer_control(self, request, pk=None):
        """
        Inning Timer & Break Stoppage Controller.
        Stoppage / break pause duration is strictly excluded from inning playing time.
        """
        match = self.get_object()
        timer, _ = LiveMatchTimerState.objects.get_or_create(match=match)
        action_cmd = request.data.get('action') # 'start', 'pause', 'break_event', 'resume', 'stop', 'config'

        now = timezone.now()

        if action_cmd == 'start':
            timer.is_running = True
            timer.is_paused = False
            timer.last_resumed_at = now
            timer.save()

        elif action_cmd == 'pause':
            # Accumulate elapsed playing time before pausing
            if timer.is_running and not timer.is_paused and timer.last_resumed_at:
                delta = int((now - timer.last_resumed_at).total_seconds())
                timer.elapsed_playing_seconds += max(0, delta)
            timer.is_running = False
            timer.is_paused = True
            timer.active_pause_reason = request.data.get('reason', 'Manual Pause')
            timer.active_pause_preset_seconds = int(request.data.get('preset_seconds', 0))
            timer.active_pause_started_at = now
            timer.save()

        elif action_cmd == 'break_event':
            # e.g., Wicket break 20s, Injury break 60s, Strategy 90s
            reason = request.data.get('reason', 'Wicket Break')
            preset_seconds = int(request.data.get('preset_seconds', 20))
            
            if timer.is_running and not timer.is_paused and timer.last_resumed_at:
                delta = int((now - timer.last_resumed_at).total_seconds())
                timer.elapsed_playing_seconds += max(0, delta)

            timer.is_running = False
            timer.is_paused = True
            timer.active_pause_reason = reason
            timer.active_pause_preset_seconds = preset_seconds
            timer.active_pause_started_at = now
            timer.save()

        elif action_cmd == 'resume':
            # Resuming playing time: calculate break duration and log as stoppage
            if timer.is_paused and timer.active_pause_started_at:
                stoppage_delta = int((now - timer.active_pause_started_at).total_seconds())
                timer.total_pause_stoppage_seconds += max(0, stoppage_delta)
                plog = list(timer.pause_events_log)
                plog.append({
                    'reason': timer.active_pause_reason or 'Break',
                    'duration_seconds': stoppage_delta,
                    'timestamp': now.isoformat()
                })
                timer.pause_events_log = plog
            timer.is_running = True
            timer.is_paused = False
            timer.active_pause_reason = ''
            timer.active_pause_started_at = None
            timer.last_resumed_at = now
            timer.save()

        elif action_cmd == 'stop':
            if timer.is_running and not timer.is_paused and timer.last_resumed_at:
                delta = int((now - timer.last_resumed_at).total_seconds())
                timer.elapsed_playing_seconds += max(0, delta)
            timer.is_running = False
            timer.is_paused = False
            timer.last_resumed_at = None
            timer.save()

        elif action_cmd == 'config':
            duration_minutes = request.data.get('inning_duration_minutes')
            reminder_seconds = request.data.get('reminder_threshold_seconds')
            if duration_minutes:
                timer.inning_duration_seconds = int(duration_minutes) * 60
            if reminder_seconds:
                timer.reminder_threshold_seconds = int(reminder_seconds)
            timer.save()

        else:
            return Response({'error': f'Unsupported timer action: {action_cmd}'}, status=status.HTTP_400_BAD_REQUEST)

        return Response(LiveMatchTimerStateSerializer(timer).data)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def set_players(self, request, pk=None):
        """Sets or swaps on-strike batsman, non-striker, and current bowler by Player ID or Club Member user_id"""
        match = self.get_object()
        scorecard, _ = LiveCricketScorecard.objects.get_or_create(match=match)

        striker_id = request.data.get('striker_id')
        non_striker_id = request.data.get('non_striker_id')
        bowler_id = request.data.get('bowler_id')

        # Support selecting a club member/employee directly
        user_id = request.data.get('user_id')
        role_target = request.data.get('target') # 'striker', 'non_striker', 'bowler'
        team_id = request.data.get('team_id')

        if user_id and role_target:
            user = User.objects.filter(id=user_id).first()
            if user:
                team = None
                if team_id:
                    team = Team.objects.filter(id=team_id).first()
                if not team:
                    team = match.team2 if role_target == 'bowler' else match.team1

                player_name = user.full_name or user.first_name or user.username
                player = Player.objects.filter(team=team, name=player_name).first()
                if not player:
                    player = Player.objects.create(team=team, name=player_name, role="Club Member / Employee")

                if role_target == 'striker':
                    scorecard.striker = player
                elif role_target == 'non_striker':
                    scorecard.non_striker = player
                elif role_target == 'bowler':
                    scorecard.current_bowler = player

        if striker_id:
            scorecard.striker = Player.objects.filter(id=striker_id).first()
        if non_striker_id:
            scorecard.non_striker = Player.objects.filter(id=non_striker_id).first()
        if bowler_id:
            scorecard.current_bowler = Player.objects.filter(id=bowler_id).first()

        scorecard.save()
        return Response(LiveCricketScorecardSerializer(scorecard).data)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def add_instant_player(self, request, pk=None):
        """
        Adds a new instant/walk-in player on the fly (who does not have an account in our system).
        Gives them a special identification role='⚡ Instant Player (Walk-in)'.
        Assigns them to the specified team and immediately sets them on the scorecard if target provided.
        """
        match = self.get_object()
        name = request.data.get('name', '').strip()
        team_id = request.data.get('team_id')
        role_target = request.data.get('target') # 'striker', 'non_striker', 'bowler'
        role_label = request.data.get('role', 'Instant Player')

        if not name:
            return Response({'error': 'Player name is required.'}, status=status.HTTP_400_BAD_REQUEST)

        team = None
        if team_id:
            team = Team.objects.filter(id=team_id).first()
        if not team:
            team = match.team2 if role_target == 'bowler' else match.team1

        player = Player.objects.create(
            team=team,
            name=name,
            role=f"⚡ {role_label} (Walk-in)",
            is_substitute=False
        )

        scorecard, _ = LiveCricketScorecard.objects.get_or_create(match=match)
        if role_target == 'striker':
            scorecard.striker = player
            scorecard.save()
        elif role_target == 'non_striker':
            scorecard.non_striker = player
            scorecard.save()
        elif role_target == 'bowler':
            scorecard.current_bowler = player
            scorecard.save()

        return Response({
            'player': {
                'id': str(player.id),
                'name': player.name,
                'role': player.role,
                'is_instant': True
            },
            'scorecard': LiveCricketScorecardSerializer(scorecard).data,
            'match': ClubMatchSerializer(match, context={'request': request}).data
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def update_match_config(self, request, pk=None):
        """Allows dynamically updating match overs, ball type, venue type during match"""
        match = self.get_object()
        custom_rules = match.custom_rules or {}
        if 'total_overs' in request.data:
            try:
                custom_rules['total_overs'] = int(request.data['total_overs'])
            except Exception:
                pass
        if 'ball_type' in request.data:
            custom_rules['ball_type'] = request.data['ball_type']
        if 'venue_type' in request.data:
            custom_rules['venue_type'] = request.data['venue_type']
        if 'ground_name' in request.data:
            custom_rules['ground_name'] = request.data['ground_name']
        match.custom_rules = custom_rules
        if 'turf_id' in request.data:
            match.turf_id = request.data['turf_id']
        match.save()
        return Response(ClubMatchSerializer(match, context={'request': request}).data)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def swap_strike(self, request, pk=None):
        """Manually swaps striker and non-striker"""
        match = self.get_object()
        scorecard, _ = LiveCricketScorecard.objects.get_or_create(match=match)
        temp = scorecard.striker
        scorecard.striker = scorecard.non_striker
        scorecard.non_striker = temp
        scorecard.save()
        return Response(LiveCricketScorecardSerializer(scorecard).data)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def score_event(self, request, pk=None):
        """
        Records a ball-by-ball cricket event:
        Runs: 0, 1, 2, 3, 4, 6
        Extras: WIDE, NO_BALL, BYE, LEG_BYE
        Wicket: BOWLED, CAUGHT, RUN_OUT, STUMPED, LBW
        Updates batsman stats, bowler stats, worm progress, and Manhattan charts.
        """
        match = self.get_object()
        scorecard, _ = LiveCricketScorecard.objects.get_or_create(match=match)

        event_type = request.data.get('type', 'RUN') # 'RUN', 'WIDE', 'NO_BALL', 'BYE', 'LEG_BYE', 'WICKET'
        runs = int(request.data.get('runs', 0))
        wicket_mode = request.data.get('wicket_mode', 'BOWLED') # 'BOWLED', 'CAUGHT', 'RUN_OUT', etc.
        out_player_id = request.data.get('out_player_id')

        striker = scorecard.striker
        bowler = scorecard.current_bowler

        striker_id = str(striker.id) if striker else 'unknown_striker'
        bowler_id = str(bowler.id) if bowler else 'unknown_bowler'

        # Initialize or retrieve batsman dictionary
        b_stats = scorecard.batsmen_stats.get(striker_id, {
            'name': striker.name if striker else 'Striker',
            'runs': 0, 'balls': 0, 'fours': 0, 'sixes': 0, 'strike_rate': 0.0, 'is_out': False, 'dismissal': ''
        })

        # Initialize or retrieve bowler dictionary
        bow_stats = scorecard.bowlers_stats.get(bowler_id, {
            'name': bowler.name if bowler else 'Bowler',
            'legal_balls': 0, 'maidens': 0, 'runs_conceded': 0, 'wickets': 0, 'economy': 0.0, 'overs': '0.0'
        })

        is_legal_ball = True
        extra_type = None

        if event_type == 'RUN':
            scorecard.total_runs += runs
            b_stats['runs'] += runs
            b_stats['balls'] += 1
            if runs == 4:
                b_stats['fours'] += 1
            elif runs == 6:
                b_stats['sixes'] += 1
            bow_stats['runs_conceded'] += runs
            bow_stats['legal_balls'] += 1

        elif event_type == 'WIDE':
            is_legal_ball = False
            extra_type = 'WIDE'
            wide_runs = 1 + runs
            scorecard.total_runs += wide_runs
            scorecard.extras['wides'] = scorecard.extras.get('wides', 0) + wide_runs
            bow_stats['runs_conceded'] += wide_runs

        elif event_type == 'NO_BALL':
            is_legal_ball = False
            extra_type = 'NO_BALL'
            nb_runs = 1 + runs
            scorecard.total_runs += nb_runs
            scorecard.extras['no_balls'] = scorecard.extras.get('no_balls', 0) + nb_runs
            b_stats['runs'] += runs
            b_stats['balls'] += 1
            bow_stats['runs_conceded'] += nb_runs

        elif event_type in ['BYE', 'LEG_BYE']:
            extra_key = 'byes' if event_type == 'BYE' else 'leg_byes'
            scorecard.total_runs += runs
            scorecard.extras[extra_key] = scorecard.extras.get(extra_key, 0) + runs
            b_stats['balls'] += 1
            bow_stats['legal_balls'] += 1

        elif event_type == 'WICKET':
            scorecard.wickets_down += 1
            b_stats['balls'] += 1
            b_stats['is_out'] = True
            b_stats['dismissal'] = f"{wicket_mode} b {bowler.name if bowler else 'Bowler'}"
            bow_stats['wickets'] += 1
            bow_stats['legal_balls'] += 1
            
            # Record fall of wicket
            fow = list(scorecard.fall_of_wickets)
            fow.append({
                'wicket_number': scorecard.wickets_down,
                'score': scorecard.total_runs,
                'overs': f"{scorecard.balls_bowled // 6}.{scorecard.balls_bowled % 6}",
                'player_name': b_stats['name']
            })
            scorecard.fall_of_wickets = fow

            # Check if wicket break pause requested (default 20s)
            auto_break = request.data.get('auto_break', True)
            if auto_break:
                timer = match.timer_state
                now = timezone.now()
                if timer.is_running and not timer.is_paused and timer.last_resumed_at:
                    delta = int((now - timer.last_resumed_at).total_seconds())
                    timer.elapsed_playing_seconds += max(0, delta)
                timer.is_running = False
                timer.is_paused = True
                timer.active_pause_reason = 'Wicket Break'
                timer.active_pause_preset_seconds = 20
                timer.active_pause_started_at = now
                timer.save()

            # Set current striker to None so scorer selects next batsman
            scorecard.striker = None

        if is_legal_ball:
            scorecard.balls_bowled += 1

        # Recompute Strike Rate
        if b_stats['balls'] > 0:
            b_stats['strike_rate'] = round((b_stats['runs'] / b_stats['balls']) * 100, 2)
        scorecard.batsmen_stats[striker_id] = b_stats

        # Recompute Economy & Bowler Overs
        overs_bowled = bow_stats['legal_balls'] / 6.0
        if overs_bowled > 0:
            bow_stats['economy'] = round(bow_stats['runs_conceded'] / overs_bowled, 2)
        comp_overs = bow_stats['legal_balls'] // 6
        rem_balls = bow_stats['legal_balls'] % 6
        bow_stats['overs'] = f"{comp_overs}.{rem_balls}"
        scorecard.bowlers_stats[bowler_id] = bow_stats

        # Strike Rotation: odd runs rotate strike (unless wicket)
        if event_type != 'WICKET' and runs % 2 != 0:
            temp = scorecard.striker
            scorecard.striker = scorecard.non_striker
            scorecard.non_striker = temp

        # Over completion: 6 legal balls rotates strike automatically
        if is_legal_ball and scorecard.balls_bowled % 6 == 0:
            temp = scorecard.striker
            scorecard.striker = scorecard.non_striker
            scorecard.non_striker = temp
            # Record Over in Manhattan and Worm
            over_num = scorecard.balls_bowled // 6
            mo = list(scorecard.manhattan_overs)
            mo.append({
                'over': over_num,
                'runs': scorecard.total_runs,
                'wickets': scorecard.wickets_down
            })
            scorecard.manhattan_overs = mo

            wp = list(scorecard.worm_progression)
            wp.append({
                'over': over_num,
                'cumulative_runs': scorecard.total_runs
            })
            scorecard.worm_progression = wp

        # Append to chronological ball events log
        be = list(scorecard.ball_events)
        be.append({
            'ball_number': scorecard.balls_bowled,
            'event': event_type,
            'runs': runs,
            'extra': extra_type,
            'striker': b_stats['name'],
            'bowler': bow_stats['name'],
            'total_score': f"{scorecard.total_runs}/{scorecard.wickets_down}",
            'timestamp': timezone.now().strftime("%H:%M:%S")
        })
        scorecard.ball_events = be

        scorecard.save()
        return Response(ClubMatchSerializer(match, context={'request': request}).data)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def finish_match(self, request, pk=None):
        """Finalizes the match outcome, records winner and updates player career profiles"""
        match = self.get_object()
        winner_id = request.data.get('winner_id')
        summary = request.data.get('summary', 'Match concluded')

        if winner_id:
            match.winner = Team.objects.filter(id=winner_id).first()
        match.result_summary = summary
        match.status = 'COMPLETED'
        match.save()

        # Stop timer
        timer = match.timer_state
        timer.is_running = False
        timer.is_paused = False
        timer.save()

        return Response(ClubMatchSerializer(match, context={'request': request}).data)
