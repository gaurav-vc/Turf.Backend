import uuid
from decimal import Decimal
from django.db import transaction
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Auction, AuctionTeam, AuctionPlayer, Bid
from .serializers import (
    AuctionSerializer, 
    AuctionTeamSerializer, 
    AuctionPlayerSerializer, 
    BidSerializer
)
from accounts.models import User, PlayerProfile
from sports.models import Team, Sport, Tournament

class AuctionViewSet(viewsets.ModelViewSet):
    queryset = Auction.objects.all().order_by('-created_at')
    serializer_class = AuctionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        tournament_id = self.request.query_params.get('tournament')
        if tournament_id:
            filtered = qs.filter(tournament_id=tournament_id)
            if not filtered.exists():
                # Check if tournament exists; if so, automatically initialize auction for this tournament
                tourn = Tournament.objects.filter(id=tournament_id).first()
                if tourn:
                    created_auction = Auction.objects.create(
                        name=f"{tourn.name} Auction",
                        organizer=self.request.user if self.request.user.is_authenticated else tourn.organizer,
                        tournament=tourn,
                        base_budget=50000.00,
                        status='ACTIVE'
                    )
                    # Automatically link tournament teams as franchise auction teams if any
                    for tt in tourn.tournament_teams.select_related('team').all():
                        if tt.team:
                            AuctionTeam.objects.get_or_create(
                                auction=created_auction,
                                team=tt.team,
                                defaults={'remaining_budget': 50000.00}
                            )
                    return Auction.objects.filter(id=created_auction.id)
            return filtered
        return qs

    def perform_create(self, serializer):
        serializer.save(organizer=self.request.user)

    @action(detail=False, methods=['post'])
    def create_full(self, request):
        """
        Full Auction Setup Wizard:
        Creates the auction, franchise teams with custom purses/wallets & captains,
        and player pool with base prices and roles all in one step.
        """
        data = request.data
        name = data.get('name', 'Turf Premier League Auction')
        base_budget = Decimal(str(data.get('base_budget', 50000.0)))
        status_val = data.get('status', 'PENDING')
        
        tournament_id = data.get('tournament') or data.get('tournament_id')
        tournament_obj = None
        if tournament_id:
            tournament_obj = Tournament.objects.filter(id=tournament_id).first()

        # Get or create default sport
        sport_id = data.get('sport_id')
        sport = None
        if sport_id:
            sport = Sport.objects.filter(id=sport_id).first()
        if not sport:
            sport = Sport.objects.first()
        if not sport:
            sport = Sport.objects.create(name='Box Cricket', slug='box-cricket', scoring_engine='runs_wickets')

        with transaction.atomic():
            auction = Auction.objects.create(
                name=name,
                organizer=request.user,
                tournament=tournament_obj,
                base_budget=base_budget,
                status=status_val
            )

            # 1. Configure Franchise Teams & Captains
            teams_data = data.get('teams', [])
            for t_data in teams_data:
                team_name = t_data.get('name') or t_data.get('team_name', 'Franchise Team')
                captain_name = t_data.get('captain_name', 'Franchise Captain')
                captain_email = t_data.get('captain_email', '')
                team_color = t_data.get('color') or t_data.get('logo_color', '#3b82f6')
                purse = Decimal(str(t_data.get('purse') or t_data.get('remaining_budget') or base_budget))

                # Find or create captain user
                captain_user = None
                if captain_email:
                    captain_user = User.objects.filter(email=captain_email).first()
                if not captain_user:
                    uname = f"cap_{uuid.uuid4().hex[:8]}"
                    c_email = captain_email or f"{uname}@turfarena.local"
                    captain_user = User.objects.create(
                        username=uname,
                        email=c_email,
                        full_name=captain_name,
                        first_name=captain_name,
                        user_type='PLAYER'
                    )

                # Find or create sports.Team
                existing_team_id = t_data.get('team_id')
                team_obj = None
                if existing_team_id:
                    team_obj = Team.objects.filter(id=existing_team_id).first()
                if not team_obj:
                    team_obj = Team.objects.create(
                        user=captain_user,
                        sport=sport,
                        name=team_name,
                        logo_color=team_color,
                        customization={'purse': float(purse)}
                    )

                # Create AuctionTeam with wallet
                AuctionTeam.objects.create(
                    auction=auction,
                    team=team_obj,
                    remaining_budget=purse
                )

            # 2. Configure Player Pool
            players_data = data.get('players', [])
            first_player = None
            for idx, p_data in enumerate(players_data):
                p_name = p_data.get('name') or p_data.get('player_name', f'Player {idx+1}')
                p_role = p_data.get('role') or p_data.get('skills', 'All-Rounder')
                p_tier = p_data.get('tier', 'Standard')
                p_base_price = Decimal(str(p_data.get('base_price', 1000.0)))

                existing_user_id = p_data.get('user_id') or p_data.get('player_id')
                player_user = None
                if existing_user_id:
                    player_user = User.objects.filter(id=existing_user_id).first()
                if not player_user:
                    uname = f"p_{uuid.uuid4().hex[:8]}"
                    p_email = f"{uname}@turfarena.local"
                    player_user = User.objects.create(
                        username=uname,
                        email=p_email,
                        full_name=p_name,
                        first_name=p_name,
                        user_type='PLAYER'
                    )
                    profile, _ = PlayerProfile.objects.get_or_create(user=player_user)
                    profile.preferences = {'role': p_role, 'tier': p_tier}
                    profile.save()

                auc_player = AuctionPlayer.objects.create(
                    auction=auction,
                    player=player_user,
                    base_price=p_base_price,
                    status='AVAILABLE'
                )

                if idx == 0 and status_val == 'ACTIVE':
                    first_player = auc_player

            # If started directly as ACTIVE, set first player on block
            if status_val == 'ACTIVE' and first_player:
                first_player.status = 'BIDDING'
                first_player.save()
                auction.active_player = first_player
                auction.save()

        return Response(AuctionSerializer(auction).data, status=status.HTTP_201_CREATED)


class AuctionTeamViewSet(viewsets.ModelViewSet):
    queryset = AuctionTeam.objects.all()
    serializer_class = AuctionTeamSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=True, methods=['post'])
    def update_purse(self, request, pk=None):
        """Adjust or set franchise wallet purse balance."""
        auc_team = self.get_object()
        new_purse = request.data.get('purse') or request.data.get('remaining_budget')
        if new_purse is not None:
            auc_team.remaining_budget = Decimal(str(new_purse))
            auc_team.save()
            return Response(AuctionTeamSerializer(auc_team).data)
        return Response({'error': 'Missing purse value'}, status=status.HTTP_400_BAD_REQUEST)


class AuctionPlayerViewSet(viewsets.ModelViewSet):
    queryset = AuctionPlayer.objects.all()
    serializer_class = AuctionPlayerSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        auction_id = self.request.query_params.get('auction')
        if auction_id:
            try:
                uuid_obj = uuid.UUID(str(auction_id))
                qs = qs.filter(auction_id=uuid_obj)
            except (ValueError, TypeError):
                # If non-UUID fallback like '1' is passed, resolve to the first available auction
                fallback_auc = Auction.objects.first()
                if fallback_auc:
                    qs = qs.filter(auction=fallback_auc)
                else:
                    qs = qs.none()
        category = self.request.query_params.get('category')
        if category and category.strip() and category.upper() != 'ALL':
            qs = qs.filter(category__iexact=category.strip())
        status_param = self.request.query_params.get('status')
        if status_param and status_param.strip():
            qs = qs.filter(status__iexact=status_param.strip())
        return qs

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        data = request.data
        name = data.get('name') or data.get('player_name')
        if name and instance.player:
            instance.player.full_name = str(name).strip()
            instance.player.first_name = str(name).strip()
            instance.player.save(update_fields=['full_name', 'first_name'])

        # Unique sequence number enforcement:
        # If user sets or edits serial_no, look for existing player with same sequence no and clear theirs to blank
        if 'serial_no' in data:
            raw_s = data.get('serial_no')
            if raw_s is None or str(raw_s).strip() in ['', 'null', 'undefined', 'None']:
                instance.serial_no = None
                instance.save(update_fields=['serial_no'])
            else:
                try:
                    s_int = int(raw_s)
                    AuctionPlayer.objects.filter(
                        auction=instance.auction,
                        serial_no=s_int
                    ).exclude(id=instance.id).update(serial_no=None)
                    instance.serial_no = s_int
                    instance.save(update_fields=['serial_no'])
                except (ValueError, TypeError):
                    pass

        if 'photo_file' in request.FILES:
            from django.core.files.storage import default_storage
            from django.conf import settings
            import os, time, secrets
            p_file = request.FILES['photo_file']
            ext = os.path.splitext(p_file.name)[1]
            safe_name = f"player_{instance.id}_{int(time.time())}_{secrets.token_hex(4)}{ext}"
            saved_path = default_storage.save(f"auction_players/{safe_name}", p_file)
            media_url = settings.MEDIA_URL if settings.MEDIA_URL.endswith('/') else f"{settings.MEDIA_URL}/"
            instance.photo_url = f"{media_url}{saved_path}"
            instance.save(update_fields=['photo_url'])

        if 'custom_data' in data:
            raw_cd = data['custom_data']
            if isinstance(raw_cd, str):
                import json
                try:
                    instance.custom_data = json.loads(raw_cd)
                except Exception:
                    pass
            elif isinstance(raw_cd, dict):
                instance.custom_data = raw_cd
            instance.save(update_fields=['custom_data'])

        return super().partial_update(request, *args, **kwargs)


class BidViewSet(viewsets.ModelViewSet):
    queryset = Bid.objects.all()
    serializer_class = BidSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        with transaction.atomic():
            auction_player = serializer.validated_data['auction_player']
            team = serializer.validated_data['team']
            amount = serializer.validated_data['amount']
            
            if amount > team.remaining_budget:
                from rest_framework.exceptions import ValidationError
                raise ValidationError(f"Insufficient budget! Team only has ₹{team.remaining_budget} left in wallet.")
                
            highest_bid = auction_player.bids.order_by('-amount').first()
            if highest_bid and amount <= highest_bid.amount:
                from rest_framework.exceptions import ValidationError
                raise ValidationError(f"Bid must be higher than current highest bid of ₹{highest_bid.amount}")

            if not highest_bid and amount < auction_player.base_price:
                from rest_framework.exceptions import ValidationError
                raise ValidationError(f"Bid cannot be lower than base price of ₹{auction_player.base_price}")
                
            serializer.save()

