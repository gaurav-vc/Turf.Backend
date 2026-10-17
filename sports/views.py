from rest_framework import viewsets, permissions
from .models import Sport, RuleSet, Team
from .serializers import SportSerializer, RuleSetSerializer, TeamSerializer

class SportViewSet(viewsets.ModelViewSet):
    queryset = Sport.objects.all().order_by('name')
    serializer_class = SportSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

class RuleSetViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = RuleSet.objects.all()
    serializer_class = RuleSetSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

class TeamViewSet(viewsets.ModelViewSet):
    serializer_class = TeamSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        mine = self.request.query_params.get('mine')

        # Restrict mutation operations to team owner unless staff
        if self.action in ['update', 'partial_update', 'destroy']:
            if user.is_authenticated and not user.is_staff:
                return Team.objects.filter(user=user)
            return Team.objects.all()

        # If client explicitly requests only owned teams
        if mine in ['true', '1'] and user.is_authenticated:
            return Team.objects.filter(user=user).order_by('-created_at')

        # Allow listing all teams for matches, tournaments, clubs, etc.
        return Team.objects.all().order_by('-created_at')

from .models import Tournament, TournamentTeam, Match
from .serializers import TournamentSerializer, TournamentTeamSerializer, MatchSerializer
from rest_framework.decorators import action
from rest_framework.response import Response

class TournamentViewSet(viewsets.ModelViewSet):
    queryset = Tournament.objects.all()
    serializer_class = TournamentSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        # Users can see their own tournaments (even private ones), plus any public tournaments.
        # But if they know the invite code, they should be able to see it. That can be handled in a retrieve.
        user = self.request.user
        if user.is_authenticated:
            from django.db.models import Q
            return Tournament.objects.filter(Q(privacy='PUBLIC') | Q(organizer=user) | Q(tournament_teams__team__user=user)).distinct()
        return Tournament.objects.filter(privacy='PUBLIC')

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def generate_bracket(self, request, pk=None):
        tournament = self.get_object()
        if tournament.organizer != request.user:
            return Response({'error': 'Only the organizer can generate the bracket.'}, status=403)
        
        teams = list(tournament.tournament_teams.filter(is_approved=True))
        if len(teams) < 2:
            return Response({'error': 'At least 2 approved teams required to generate a bracket.'}, status=400)
            
        import random
        import math
        random.shuffle(teams)
        
        tournament.matches.all().delete()
        
        num_teams = len(teams)
        num_rounds = math.ceil(math.log2(num_teams))
        total_slots = 2 ** num_rounds
        
        current_round_matches = []
        
        # Round 1
        for i in range(0, total_slots, 2):
            team1 = teams[i].team if i < num_teams else None
            team2 = teams[i+1].team if i+1 < num_teams else None
            
            # If both are None, this is a ghost match (should only happen if extreme byes)
            # If one is None, the other gets a bye and wins automatically
            winner = None
            status = 'SCHEDULED'
            
            if team1 and not team2:
                winner = team1
                status = 'COMPLETED'
            elif team2 and not team1:
                winner = team2
                status = 'COMPLETED'
            elif not team1 and not team2:
                status = 'COMPLETED'
                
            match = Match.objects.create(
                tournament=tournament,
                team1=team1,
                team2=team2,
                round_name='Finals' if num_rounds == 1 else 'Round 1',
                match_order=i//2 + 1,
                winner=winner,
                status=status
            )
            current_round_matches.append(match)
            
        # Build subsequent rounds
        for round_idx in range(2, num_rounds + 1):
            next_round_matches = []
            
            if round_idx == num_rounds:
                round_name = 'Finals'
            elif round_idx == num_rounds - 1:
                round_name = 'Semi Finals'
            elif round_idx == num_rounds - 2:
                round_name = 'Quarter Finals'
            else:
                round_name = f'Round {round_idx}'
                
            for i in range(0, len(current_round_matches), 2):
                prev_match1 = current_round_matches[i]
                prev_match2 = current_round_matches[i+1]
                
                t1 = prev_match1.winner
                t2 = prev_match2.winner
                
                winner = None
                status = 'SCHEDULED'
                
                # Auto-advance if previous matches were ghost/bye matches
                if t1 and not t2 and prev_match2.status == 'COMPLETED':
                    winner = t1
                    status = 'COMPLETED'
                elif t2 and not t1 and prev_match1.status == 'COMPLETED':
                    winner = t2
                    status = 'COMPLETED'
                elif not t1 and not t2 and prev_match1.status == 'COMPLETED' and prev_match2.status == 'COMPLETED':
                    status = 'COMPLETED'
                
                match = Match.objects.create(
                    tournament=tournament,
                    team1=t1,
                    team2=t2,
                    round_name=round_name,
                    match_order=i//2 + 1,
                    winner=winner,
                    status=status
                )
                
                prev_match1.next_match = match
                prev_match1.save()
                prev_match2.next_match = match
                prev_match2.save()
                
                next_round_matches.append(match)
                
            current_round_matches = next_round_matches
        
        tournament.status = 'ONGOING'
        tournament.save()
        return Response({'status': 'Bracket generated successfully'})

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def invite_team(self, request, pk=None):
        tournament = self.get_object()
        if tournament.organizer != request.user:
            return Response({'error': 'Only the organizer can invite teams.'}, status=403)
        
        team_id = request.data.get('team_id')
        if not team_id:
            return Response({'error': 'team_id is required'}, status=400)
            
        try:
            team = Team.objects.get(id=team_id)
        except Team.DoesNotExist:
            return Response({'error': 'Team not found'}, status=404)
            
        if tournament.tournament_teams.filter(team=team).exists():
            return Response({'error': 'Team is already registered.'}, status=400)
            
        from accounts.models import Notification
        msg = f"You have been invited to join the tournament '{tournament.name}' with your team '{team.name}'."
        if tournament.privacy == 'PRIVATE':
            msg += f" (Invite Code: {tournament.invite_code})"
            
        Notification.objects.create(
            user=team.user,
            title="Tournament Invitation",
            message=msg,
            type="TEAM_INVITE",
            link=f"/tournaments/{tournament.id}"
        )
        return Response({'status': 'Invitation sent successfully!'})

class TournamentTeamViewSet(viewsets.ModelViewSet):
    queryset = TournamentTeam.objects.all()
    serializer_class = TournamentTeamSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        # A user can join their own team to a tournament
        # Or organizer can add a team. 
        serializer.save()

class MatchViewSet(viewsets.ModelViewSet):
    queryset = Match.objects.all()
    serializer_class = MatchSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def perform_update(self, serializer):
        match = serializer.save()
        # If score entered and winner chosen, advance the winner
        if match.winner and match.next_match:
            # Add winner to next match
            if not match.next_match.team1:
                match.next_match.team1 = match.winner
            else:
                match.next_match.team2 = match.winner
            match.next_match.save()
