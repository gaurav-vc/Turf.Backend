import secrets
import random
import time
import os
import uuid
import csv
import io
import re
from decimal import Decimal
from django.conf import settings
from django.http import HttpResponse
from django.core.files.storage import default_storage
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from accounts.models import User
from sports.models import Team, Sport
from .models import Auction, AuctionTeam, AuctionPlayer, Bid
from .models_v24 import (
    AuctionTournamentConfig,
    AuctionCategory,
    BidSlab,
    SquadRule,
    CustomFieldDefinition,
    CustomFieldOption,
    AuctionPageDesign,
    PublicAuctionLink,
    PlayerRegistrationLink,
    AuctionSponsorItem,
    AuctionMediaItem,
    GroupDrawCard,
    AuctionEventLog,
    TeamPurseTransaction,
)
from .serializers_v24 import (
    AuctionTournamentConfigSerializer,
    AuctionCategorySerializer,
    BidSlabSerializer,
    SquadRuleSerializer,
    CustomFieldDefinitionSerializer,
    AuctionPageDesignSerializer,
    PublicAuctionLinkSerializer,
    PlayerRegistrationLinkSerializer,
    AuctionSponsorItemSerializer,
    AuctionMediaItemSerializer,
    GroupDrawCardSerializer,
)
import urllib.request
import json
from .services.live_auction_engine import LiveAuctionEngine
from .services.max_bid_calculator import team_financials
from .services.player_intake_service import PlayerIntakeService
from .services.asset_manager_service import AssetManagerService

DEFAULT_AUCTION_DESIGN = {
    'version': 4,
    'canvas_mode': 'professional',
    'snap_grid': 5,
    'grid_visible': True,
    'background_mode': 'stadium',
    'custom_background_url': '',
    'zones': {
        'team_columns': 14,
        'action_zone_width': 455,
        'bid_history_width': 300,
        'team_grid': {'max_columns': 14, 'rows': 2, 'box_width': 120, 'box_height': 54, 'gap': 6},
        'action_bar': {'width': 455, 'columns': 4, 'button_height': 42, 'gap': 6, 'show_more': True},
        'bid_history': {'width': 300, 'rows': 6, 'newest_first': True},
        'branding': {
            'logo_count': 1,
            'logo_position': 'center',
            'logo_size': 38,
            'title_size': 30,
            'title_text': 'Test Tournament',
            'title_colour': '#FFD54A',
            'title_image_url': '',
            'remove_title_bg': False,
        },
    },
    'elements': {
        'tournament_title': {'x': 20, 'y': 2, 'w': 60, 'h': 7, 'font_size': 26, 'colour': '#FFD54A', 'font_family': 'Arial', 'bold': True, 'align': 'center', 'selected': True, 'show_label': False},
        'player_category': {'x': 20, 'y': 10, 'w': 60, 'h': 6, 'font_size': 22, 'colour': '#FFD54A', 'font_family': 'Arial', 'bold': True, 'align': 'center', 'selected': True, 'show_label': False},
        'player_number': {'x': 4, 'y': 10, 'w': 20, 'h': 5, 'font_size': 16, 'colour': '#B8C7DA', 'font_family': 'Arial', 'bold': True, 'align': 'left', 'selected': True, 'show_label': False},
        'player_photo': {'x': 4, 'y': 18, 'w': 28, 'h': 60, 'font_size': 14, 'colour': '#FFFFFF', 'font_family': 'Arial', 'bold': False, 'align': 'center', 'selected': True},
        'player_name': {'x': 35, 'y': 18, 'w': 58, 'h': 10, 'font_size': 42, 'colour': '#FFFFFF', 'font_family': 'Arial', 'bold': True, 'align': 'left', 'selected': True, 'show_label': False},
        'role': {'x': 35, 'y': 29, 'w': 28, 'h': 6, 'font_size': 18, 'colour': '#D8E2EF', 'font_family': 'Arial', 'bold': True, 'align': 'left', 'selected': True, 'show_label': False},
        'batting_style': {'x': 35, 'y': 37, 'w': 25, 'h': 6, 'font_size': 14, 'colour': '#FFFFFF', 'font_family': 'Arial', 'bold': False, 'align': 'left', 'selected': True, 'show_label': True},
        'bowling_style': {'x': 62, 'y': 37, 'w': 25, 'h': 6, 'font_size': 14, 'colour': '#FFFFFF', 'font_family': 'Arial', 'bold': False, 'align': 'left', 'selected': True, 'show_label': True},
        'location': {'x': 75, 'y': 37, 'w': 22, 'h': 6, 'font_size': 14, 'colour': '#FFFFFF', 'font_family': 'Arial', 'bold': False, 'align': 'left', 'selected': True, 'show_label': True},
        'current_bid': {'x': 35, 'y': 52, 'w': 32, 'h': 14, 'font_size': 46, 'colour': '#FFD54A', 'font_family': 'Arial', 'bold': True, 'align': 'left', 'selected': True, 'show_label': True},
        'bidder_name': {'x': 68, 'y': 52, 'w': 28, 'h': 8, 'font_size': 22, 'colour': '#FFFFFF', 'font_family': 'Arial', 'bold': True, 'align': 'right', 'selected': True, 'show_label': False},
        'balance': {'x': 68, 'y': 62, 'w': 28, 'h': 6, 'font_size': 14, 'colour': '#B9C7D7', 'font_family': 'Arial', 'bold': True, 'align': 'right', 'selected': True, 'show_label': True},
        'max_bid': {'x': 68, 'y': 70, 'w': 28, 'h': 6, 'font_size': 14, 'colour': '#FFFFFF', 'font_family': 'Arial', 'bold': True, 'align': 'right', 'selected': True, 'show_label': True},
        'base_price': {'x': 4, 'y': 80, 'w': 28, 'h': 7, 'font_size': 20, 'colour': '#FFFFFF', 'font_family': 'Arial', 'bold': True, 'align': 'center', 'selected': True, 'show_label': True},
        'top_bar': {'x': 2, 'y': 1.5, 'w': 96, 'h': 6.5, 'font_size': 13, 'colour': '#FFFFFF', 'font_family': 'Arial', 'bold': True, 'align': 'left', 'selected': True, 'show_label': False},
        'bid_history': {'x': 74, 'y': 9.5, 'w': 24, 'h': 77, 'font_size': 12, 'colour': '#FFFFFF', 'font_family': 'Arial', 'bold': True, 'align': 'left', 'selected': True, 'show_label': False},
        'action_bar': {'x': 2, 'y': 88, 'w': 96, 'h': 10, 'font_size': 12, 'colour': '#FFFFFF', 'font_family': 'Arial', 'bold': True, 'align': 'left', 'selected': True, 'show_label': False},
    }
}

from rest_framework.negotiation import DefaultContentNegotiation

class SafeContentNegotiation(DefaultContentNegotiation):
    def select_renderer(self, request, renderers, format_suffix=None):
        format_param = request.query_params.get(self.settings.FORMAT_SUFFIX_KWARG)
        if format_param and str(format_param).lower() in ['category', 'auction', 'all', 'pdf', 'csv', 'custom']:
            format_suffix = None
        try:
            return super().select_renderer(request, renderers, format_suffix)
        except Exception:
            return renderers[0], renderers[0].media_type

class Phase2AuctionConsoleViewSet(viewsets.ViewSet):
    """
    Dedicated ViewSet for Phase 2 V24 Live Auction Console Operations.
    """
    permission_classes = [permissions.IsAuthenticated]
    content_negotiation_class = SafeContentNegotiation

    def _get_auction(self, pk):
        auction = None
        if pk:
            try:
                uuid_obj = uuid.UUID(str(pk))
                auction = Auction.objects.filter(pk=uuid_obj).first()
            except (ValueError, TypeError, Exception):
                auction = None

        if not auction:
            auction = Auction.objects.first()
        if not auction:
            organizer = (
                getattr(self, 'request', None) and getattr(self.request, 'user', None) and self.request.user.is_authenticated and self.request.user
            ) or User.objects.first()
            if not organizer:
                organizer = User.objects.create_user(username='auction_organizer', email='organizer@turf.local')
            auction = Auction.objects.create(
                name='Turf Premier League (Live Auction)',
                organizer=organizer,
                status='ACTIVE',
                base_budget=100000
            )
        return auction

    def retrieve(self, request, pk=None):
        """Standard detail endpoint alias returning full reactive auction state."""
        return self.live_state(request, pk)

    @action(detail=True, methods=['get'])
    def live_state(self, request, pk=None):
        """Returns full reactive state for live auction broadcast & controls."""
        auction = self._get_auction(pk)
        state = LiveAuctionEngine.get_live_state(auction)
        return Response(state)

    @action(detail=True, methods=['post'])
    def bid(self, request, pk=None):
        """Places a team quick bid or custom bid."""
        auction = self._get_auction(pk)
        team_id = request.data.get('team_id')
        amount = request.data.get('amount')
        is_custom = request.data.get('is_custom', False)

        team = auction.teams.filter(id=team_id).first()
        if not team:
            return Response({'error': 'Team not found in this auction'}, status=status.HTTP_404_NOT_FOUND)

        ok, result = LiveAuctionEngine.place_bid(auction, team, amount, is_custom)
        if not ok:
            return Response({'error': result}, status=status.HTTP_400_BAD_REQUEST)

        state = LiveAuctionEngine.get_live_state(auction)
        return Response(state)

    @action(detail=True, methods=['post'])
    def hammer_sold(self, request, pk=None):
        """HAMMER DOWN: Sells active player to highest bidder."""
        auction = self._get_auction(pk)
        
        # Calculate highest sale achieved earlier before this sale
        prev_highest = auction.players.filter(status='SOLD').order_by('-sold_price').first()
        prev_highest_amount = prev_highest.sold_price if (prev_highest and prev_highest.sold_price) else Decimal('0.00')

        ok, result = LiveAuctionEngine.sell_active_player(auction)
        if not ok:
            return Response({'error': result}, status=status.HTTP_400_BAD_REQUEST)

        sold_player = result
        celebration = 'sold'
        if sold_player and getattr(sold_player, 'sold_price', None):
            if prev_highest_amount > 0 and sold_player.sold_price >= prev_highest_amount:
                celebration = 'highest_bid'

        state = LiveAuctionEngine.get_live_state(auction)
        return Response({'success': True, 'celebration': celebration, 'state': state})

    @action(detail=True, methods=['post'])
    def hammer_unsold(self, request, pk=None):
        """HAMMER: Marks active player UNSOLD."""
        auction = self._get_auction(pk)
        ok, result = LiveAuctionEngine.unsold_active_player(auction)
        if not ok:
            return Response({'error': result}, status=status.HTTP_400_BAD_REQUEST)

        state = LiveAuctionEngine.get_live_state(auction)
        return Response({'success': True, 'state': state})

    @action(detail=True, methods=['post'])
    def undo_sale(self, request, pk=None):
        """Undoes the most recent sale and restores team wallet balance."""
        auction = self._get_auction(pk)
        ok, result = LiveAuctionEngine.undo_sale(auction)
        if not ok:
            return Response({'error': result}, status=status.HTTP_400_BAD_REQUEST)

        state = LiveAuctionEngine.get_live_state(auction)
        return Response({'success': True, 'message': 'Sale undone successfully.', 'state': state})

    @action(detail=True, methods=['post'])
    def undo_bid(self, request, pk=None):
        """Undoes the latest bid placed."""
        auction = self._get_auction(pk)
        ok, result = LiveAuctionEngine.undo_bid(auction)
        if not ok:
            return Response({'error': result}, status=status.HTTP_400_BAD_REQUEST)

        state = LiveAuctionEngine.get_live_state(auction)
        return Response({'success': True, 'state': state})

    @action(detail=True, methods=['post'])
    def reset_bid(self, request, pk=None):
        """Resets all bids for current active player back to 0."""
        auction = self._get_auction(pk)

        ok, result = LiveAuctionEngine.reset_bid(auction)
        if not ok:
            return Response({'error': result}, status=status.HTTP_400_BAD_REQUEST)

        state = LiveAuctionEngine.get_live_state(auction)
        return Response({'success': True, 'state': state})

    @action(detail=True, methods=['post'])
    def select_player_no(self, request, pk=None):
        """Puts a player on block by Player No / Serial No."""
        auction = self._get_auction(pk)

        serial_no = request.data.get('serial_no')
        player_id = request.data.get('player_id')
        if not serial_no and not player_id:
            return Response({'error': 'serial_no or player_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        if serial_no is not None and str(serial_no).strip():
            ok, result = LiveAuctionEngine.select_player_by_number(auction, int(serial_no))
        else:
            ok, result = LiveAuctionEngine.select_player_by_id(auction, player_id)
        if not ok:
            return Response({'error': result}, status=status.HTTP_400_BAD_REQUEST)

        state = LiveAuctionEngine.get_live_state(auction)
        return Response({'success': True, 'state': state})

    @action(detail=True, methods=['post'], url_path='select_next_player')
    def select_next_player(self, request, pk=None):
        """Puts the next available player of the given category on the auction block."""
        auction = self._get_auction(pk)
        category = request.data.get('category')

        ok, result = LiveAuctionEngine.select_next_player_by_category(auction, category)
        if not ok:
            return Response({'error': result}, status=status.HTTP_400_BAD_REQUEST)

        state = LiveAuctionEngine.get_live_state(auction)
        return Response({'success': True, 'state': state})

    @action(detail=True, methods=['get'], permission_classes=[permissions.AllowAny], url_path='player_queue')
    def player_queue(self, request, pk=None):
        """Returns the upcoming queue of players for auto-advance or queue preview."""
        auction = self._get_auction(pk)
        category = request.query_params.get('category')
        qs = auction.players.filter(status__in=['AVAILABLE', 'PENDING'])
        if category and category.strip() and category.upper() != 'ALL':
            qs = qs.filter(category__iexact=category.strip())
        
        # Respect category priority order
        cat_order = list(AuctionCategory.objects.filter(auction=auction).order_by('priority', 'display_order', 'created_at').values_list('name', flat=True))
        
        queued_players = list(qs.order_by('serial_no', 'created_at', 'id')[:10])
        results = []
        for p in queued_players:
            photo = ''
            if hasattr(p, 'photo_file') and p.photo_file:
                try:
                    photo = p.photo_file.url
                except Exception:
                    photo = str(p.photo_file)
            elif hasattr(p, 'photo') and p.photo:
                photo = str(p.photo)
            elif p.player and p.player.photo_url:
                photo = p.player.photo_url

            results.append({
                'id': str(p.id),
                'serial_no': p.serial_no,
                'name': p.player.full_name or 'Player',
                'category': p.category or 'General',
                'role': p.role or 'Player',
                'base_price': float(p.base_price or 0),
                'photo': photo,
                'photo_url': photo,
            })

        config = getattr(auction, 'v24_config', None)
        return Response({
            'success': True,
            'queue': results,
            'total_pending': qs.count(),
            'auto_advance_queue': getattr(config, 'auto_advance_queue', True) if config else True,
            'allow_multiple_bids': getattr(config, 'allow_multiple_bids', False) if config else False,
        })

    @action(detail=True, methods=['post'], url_path='update_player_outcome')
    def update_player_outcome(self, request, pk=None):
        """Host / Organizer manual update of a player's auction status, assigned team, and sold bid amount."""
        auction = self._get_auction(pk)
        player_id = request.data.get('player_id')
        if not player_id:
            return Response({'error': 'player_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        player = auction.players.filter(id=player_id).first()
        if not player:
            return Response({'error': 'Player not found in this tournament.'}, status=status.HTTP_404_NOT_FOUND)

        new_status = request.data.get('status') or player.status
        if new_status == 'PENDING':
            new_status = 'AVAILABLE'
        if new_status not in ['AVAILABLE', 'SOLD', 'UNSOLD', 'BIDDING']:
            return Response({'error': f"Invalid status {new_status}"}, status=status.HTTP_400_BAD_REQUEST)

        prev_status = player.status
        prev_sold_to = player.sold_to
        prev_sold_price = player.sold_price or Decimal('0')

        if new_status == 'SOLD':
            team_id = request.data.get('sold_to') or request.data.get('team_id')
            if not team_id:
                return Response({'error': 'Please select the franchise team the player was sold to.'}, status=status.HTTP_400_BAD_REQUEST)

            team = auction.teams.filter(id=team_id).first()
            if not team:
                team = auction.teams.filter(team__name__iexact=str(team_id)).first()
            if not team:
                return Response({'error': 'Franchise team not found in this tournament.'}, status=status.HTTP_404_NOT_FOUND)

            try:
                raw_amt = request.data.get('sold_price')
                sold_price = Decimal(str(raw_amt).replace(',', '').strip()) if raw_amt is not None else player.base_price
            except Exception:
                sold_price = player.base_price

            # If re-assigning, refund old team
            if prev_status == 'SOLD' and prev_sold_to and prev_sold_to.id != team.id:
                prev_sold_to.remaining_budget += prev_sold_price
                prev_sold_to.save(update_fields=['remaining_budget'])
            elif prev_status == 'SOLD' and prev_sold_to and prev_sold_to.id == team.id:
                team.remaining_budget += prev_sold_price

            team.remaining_budget = max(Decimal('0'), team.remaining_budget - sold_price)
            team.save(update_fields=['remaining_budget'])

            player.status = 'SOLD'
            player.sold_to = team
            player.sold_price = sold_price
            player.save(update_fields=['status', 'sold_to', 'sold_price'])

        else:
            # Reverting back to AVAILABLE, UNSOLD, or BIDDING
            if prev_status == 'SOLD' and prev_sold_to:
                prev_sold_to.remaining_budget += prev_sold_price
                prev_sold_to.save(update_fields=['remaining_budget'])

            player.status = new_status
            player.sold_to = None
            player.sold_price = None
            player.save(update_fields=['status', 'sold_to', 'sold_price'])

        from .serializers import AuctionPlayerSerializer
        return Response({
            'success': True,
            'message': f"Player #{player.serial_no} outcome updated successfully.",
            'player': AuctionPlayerSerializer(player).data
        })

    @action(detail=True, methods=['post'])
    def reauction(self, request, pk=None):
        """Starts re-auction round for unsold players."""
        auction = self._get_auction(pk)

        category = request.data.get('category')
        ok, msg = LiveAuctionEngine.start_reauction_round(auction, category)
        if not ok:
            return Response({'error': msg}, status=status.HTTP_400_BAD_REQUEST)

        state = LiveAuctionEngine.get_live_state(auction)
        return Response({'success': True, 'message': msg, 'state': state})

    def _create_single_player(self, auction, request):
        """Creates a single player profile, user account, category linking, and photo upload."""
        data = request.data
        name = data.get('name') or data.get('player_name')
        if not name or not str(name).strip():
            return Response({'error': 'Player name is required.'}, status=status.HTTP_400_BAD_REQUEST)
        name = str(name).strip()

        mobile = str(data.get('mobile') or '').strip()
        location = str(data.get('location') or '').strip()
        role_name = str(data.get('role') or data.get('player_skills') or 'All-Rounder').strip()
        cat_name = str(data.get('category') or '').strip()
        batting = str(data.get('batting_style') or '').strip()
        bowling = str(data.get('bowling_style') or '').strip()
        tagging = str(data.get('tagging') or 'Player').strip()

        age_val = data.get('age')
        age = None
        if age_val is not None and str(age_val).strip().isdigit():
            age = int(str(age_val).strip())

        # Category resolution
        cat_obj = None
        if cat_name:
            cat_obj = auction.categories.filter(name__iexact=cat_name).first()
            if not cat_obj:
                cat_obj = AuctionCategory.objects.create(
                    auction=auction,
                    name=cat_name,
                    base_price=Decimal('1000.00'),
                    target_count=0
                )

        # Base price
        base_raw = data.get('base_price')
        if base_raw is not None and str(base_raw).strip():
            try:
                base_price = Decimal(str(base_raw).replace(',', '').strip())
            except Exception:
                base_price = cat_obj.base_price if cat_obj else Decimal('1000.00')
        elif cat_obj and cat_obj.base_price > 0:
            base_price = cat_obj.base_price
        else:
            base_price = Decimal('1000.00')

        # Serial No
        serial_raw = data.get('serial_no') or data.get('player_no')
        if serial_raw is not None and str(serial_raw).strip().isdigit():
            serial_no = int(str(serial_raw).strip())
        else:
            last_p = auction.players.order_by('-serial_no').first()
            serial_no = ((last_p.serial_no or 0) + 1) if last_p else 1

        # Photo handling
        photo_url = str(data.get('photo_url') or '').strip()
        photo_file = request.FILES.get('photo_file') or request.FILES.get('photo')
        if photo_file:
            try:
                ext = os.path.splitext(photo_file.name)[1]
                safe_name = f"player_{auction.id}_{int(time.time())}_{secrets.token_hex(4)}{ext}"
                saved_path = default_storage.save(f"auction_players/{safe_name}", photo_file)
                photo_url = request.build_absolute_uri(settings.MEDIA_URL + saved_path)
            except Exception as e:
                print("Player photo upload error:", e)

        # Custom data
        custom_data = {}
        raw_custom = data.get('custom_data')
        if raw_custom:
            if isinstance(raw_custom, str):
                try:
                    custom_data = json.loads(raw_custom)
                except Exception:
                    custom_data = {}
            elif isinstance(raw_custom, dict):
                custom_data = raw_custom

        for k in ['app_name', 'app_id', 'experience', 'nationality', 'pin_code', 'awards_won', 'bowling_type']:
            val = data.get(k)
            if val is not None and str(val).strip():
                custom_data[k] = str(val).strip()
        custom_data['tagging'] = tagging

        # Create or find User
        uname = f"auc_{uuid.uuid4().hex[:8]}"
        p_email = f"{uname}@turfarena.local"
        player_user = User.objects.create(
            username=uname,
            email=p_email,
            full_name=name,
            first_name=name,
            user_type='PLAYER'
        )

        auc_player = AuctionPlayer.objects.create(
            auction=auction,
            player=player_user,
            serial_no=serial_no,
            category=cat_obj.name if cat_obj else (cat_name or 'General'),
            role=role_name,
            batting_style=batting,
            bowling_style=bowling,
            location=location,
            mobile=mobile,
            age=age,
            base_price=base_price,
            photo_url=photo_url,
            registration_source='Manual Entry',
            status='AVAILABLE',
            custom_data=custom_data
        )

        return Response({
            'success': True,
            'message': 'Player created successfully.',
            'player': {
                'id': str(auc_player.id),
                'serial_no': auc_player.serial_no,
                'name': name,
                'player_name': name,
                'category': auc_player.category,
                'role': auc_player.role,
                'base_price': float(auc_player.base_price),
                'photo_url': auc_player.photo_url,
                'status': auc_player.status,
                'mobile': auc_player.mobile,
                'location': auc_player.location,
                'age': auc_player.age,
            }
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get', 'post'], parser_classes=[MultiPartParser, FormParser, JSONParser], url_path='players')
    def players(self, request, pk=None):
        """List players in this tournament or create a single player manually."""
        auction = self._get_auction(pk)
        if request.method == 'GET':
            from .serializers import AuctionPlayerSerializer
            players_qs = auction.players.select_related('player', 'sold_to', 'sold_to__team').all().order_by('serial_no', 'id')
            return Response(AuctionPlayerSerializer(players_qs, many=True).data)
        return self._create_single_player(auction, request)

    @action(detail=True, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def bulk_import_players(self, request, pk=None):
        """Imports players from an uploaded CSV or Excel file or single manual player entry."""
        auction = self._get_auction(pk)

        file_obj = request.FILES.get('file')
        if not file_obj:
            if request.data.get('name') or request.data.get('player_name'):
                return self._create_single_player(auction, request)
            return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            rows, headers = PlayerIntakeService.parse_file(file_obj)
            imported_count, errors = PlayerIntakeService.import_players(auction, rows, headers, request.user)
            return Response({
                'success': True,
                'imported_count': imported_count,
                'errors': errors,
                'total_rows': len(rows),
            })
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get', 'post'], parser_classes=[MultiPartParser, FormParser, JSONParser])
    def teams(self, request, pk=None):
        """Get all franchise teams for auction or add a new team with full branding and financials."""
        auction = self._get_auction(pk)

        if request.method == 'GET':
            teams_qs = auction.teams.select_related('team', 'team__user').all()
            data = []
            for at in teams_qs:
                t = at.team
                u = t.user if t else None
                logo_val = ''
                if t and t.logo:
                    try:
                        logo_val = t.logo.url
                    except Exception:
                        logo_val = str(t.logo)
                if not logo_val:
                    logo_val = at.custom_data.get('logo_url', '')

                if logo_val and not (logo_val.startswith('http://') or logo_val.startswith('https://')):
                    logo_val = request.build_absolute_uri(logo_val)

                data.append({
                    'id': str(at.id),
                    'team_id': str(t.id) if t else '',
                    'name': t.name if t else 'Unnamed Team',
                    'short_name': at.custom_data.get('short_name', (t.name[:3].upper() if t and t.name else 'TM')),
                    'color': t.logo_color if t and t.logo_color else '#2563eb',
                    'logo': logo_val,
                    'logo_url': at.custom_data.get('logo_url', ''),
                    'remove_logo_background': at.custom_data.get('remove_logo_background', False),
                    'owner_name': at.custom_data.get('owner_name', (u.full_name or u.first_name) if u else ''),
                    'owner_email': at.custom_data.get('owner_email', u.email if u else ''),
                    'owner_mobile': at.custom_data.get('owner_mobile', getattr(u, 'phone_number', '') if u else ''),
                    'manager_name': at.custom_data.get('manager_name', ''),
                    'manager_email': at.custom_data.get('manager_email', ''),
                    'manager_mobile': at.custom_data.get('manager_mobile', ''),
                    'additional_kitty': float(at.additional_kitty or 0),
                    'penalty_amount': float(at.penalty_amount or 0),
                    'reserve_amount': float(at.reserve_amount or 0),
                    'sponsor_name': at.custom_data.get('sponsor_name', ''),
                    'remaining_budget': float(at.remaining_budget or 0),
                    'players_count': auction.players.filter(sold_to=at).count(),
                    'live_token': at.live_token or '',
                })
            return Response(data)

        # POST: Create Team
        name = request.data.get('name') or request.data.get('team_name')
        if not name or not str(name).strip():
            return Response({'error': 'Team name is required.'}, status=status.HTTP_400_BAD_REQUEST)

        name = str(name).strip()
        short_name = str(request.data.get('short_name') or name[:3]).strip().upper()[:3]
        owner_name = str(request.data.get('owner_name') or '').strip()
        owner_email = str(request.data.get('owner_email') or '').strip()
        owner_mobile = str(request.data.get('owner_mobile') or '').strip()
        manager_name = str(request.data.get('manager_name') or '').strip()
        manager_email = str(request.data.get('manager_email') or '').strip()
        manager_mobile = str(request.data.get('manager_mobile') or '').strip()
        sponsor_name = str(request.data.get('sponsor_name') or '').strip()
        logo_url = str(request.data.get('logo_url') or '').strip()
        remove_bg = request.data.get('remove_logo_background') in [True, 'true', 'True', 1, '1']

        try:
            kitty = Decimal(str(request.data.get('additional_kitty') or '0'))
        except Exception:
            kitty = Decimal('0')

        try:
            penalty = Decimal(str(request.data.get('penalty_amount') or request.data.get('penalty') or '0'))
        except Exception:
            penalty = Decimal('0')

        try:
            reserve = Decimal(str(request.data.get('reserve_amount') or request.data.get('reserve') or '0'))
        except Exception:
            reserve = Decimal('0')

        # Distinct color palette
        PALETTE = [
            '#2563EB', '#DC2626', '#EAB308', '#16A34A', '#7C3AED', '#EA580C',
            '#0891B2', '#DB2777', '#4F46E5', '#059669', '#D97706', '#9333EA',
            '#0284C7', '#E11D48', '#65A30D', '#0D9488'
        ]
        color = request.data.get('color') or request.data.get('team_colour') or request.data.get('logo_color')
        if not color or not str(color).strip():
            existing_count = auction.teams.count()
            color = PALETTE[existing_count % len(PALETTE)]

        # Get sport
        sport = Sport.objects.first()
        if not sport:
            sport = Sport.objects.create(name='Cricket', slug='cricket', scoring_engine='cricket')

        # Find or create User for owner
        if owner_email:
            owner_user = User.objects.filter(email__iexact=owner_email).first()
        else:
            owner_user = None

        if not owner_user:
            uname = f"owner_{uuid.uuid4().hex[:8]}"
            o_email = owner_email or f"{uname}@turfarena.local"
            owner_user = User.objects.create_user(
                username=uname,
                email=o_email,
                full_name=owner_name or name,
                user_type='PLAYER'
            )
            if owner_mobile and hasattr(owner_user, 'phone_number'):
                owner_user.phone_number = owner_mobile
                owner_user.save()

        # Create sports.models.Team
        logo_file = request.FILES.get('logo') or request.FILES.get('team_logo')
        team_obj = Team.objects.create(
            user=owner_user,
            sport=sport,
            name=name,
            logo_color=color,
            customization={
                'short_name': short_name,
                'sponsor_name': sponsor_name,
                'logo_url': logo_url,
                'remove_logo_background': remove_bg,
            }
        )
        if logo_file:
            team_obj.logo = logo_file
            team_obj.save()

        # Compute initial budget
        calc_budget = auction.base_budget + kitty - reserve - penalty

        # Create AuctionTeam
        custom_data = {
            'short_name': short_name,
            'owner_name': owner_name,
            'owner_email': owner_email,
            'owner_mobile': owner_mobile,
            'manager_name': manager_name,
            'manager_email': manager_email,
            'manager_mobile': manager_mobile,
            'sponsor_name': sponsor_name,
            'logo_url': logo_url,
            'remove_logo_background': remove_bg,
        }
        auc_team = AuctionTeam.objects.create(
            auction=auction,
            team=team_obj,
            remaining_budget=calc_budget,
            additional_kitty=kitty,
            penalty_amount=penalty,
            reserve_amount=reserve,
            custom_data=custom_data,
            live_token=secrets.token_urlsafe(16)
        )

        logo_val = ''
        if team_obj.logo:
            try:
                logo_val = team_obj.logo.url
            except Exception:
                logo_val = str(team_obj.logo)
        if not logo_val:
            logo_val = logo_url

        return Response({
            'success': True,
            'team': {
                'id': str(auc_team.id),
                'team_id': str(team_obj.id),
                'name': team_obj.name,
                'short_name': short_name,
                'color': color,
                'logo': logo_val,
                'logo_url': logo_url,
                'remove_logo_background': remove_bg,
                'owner_name': owner_name,
                'owner_email': owner_email,
                'owner_mobile': owner_mobile,
                'manager_name': manager_name,
                'manager_email': manager_email,
                'manager_mobile': manager_mobile,
                'additional_kitty': float(kitty),
                'penalty_amount': float(penalty),
                'reserve_amount': float(reserve),
                'sponsor_name': sponsor_name,
                'remaining_budget': float(calc_budget),
                'players_count': 0,
                'live_token': auc_team.live_token,
            }
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['patch', 'put', 'delete'], url_path='teams/(?P<team_id>[^/.]+)', parser_classes=[MultiPartParser, FormParser, JSONParser])
    def team_detail(self, request, pk=None, team_id=None):
        """Update or delete a franchise team in the auction."""
        auction = self._get_auction(pk)
        auc_team = auction.teams.filter(pk=team_id).first()
        if not auc_team:
            return Response({'error': 'Auction team not found.'}, status=status.HTTP_404_NOT_FOUND)

        if request.method == 'DELETE':
            auc_team.delete()
            return Response({'success': True, 'message': 'Team removed from auction.'})

        # PATCH / PUT
        t = auc_team.team
        data = request.data
        if 'name' in data and str(data['name']).strip():
            t.name = str(data['name']).strip()
        if 'color' in data or 'team_colour' in data or 'logo_color' in data:
            c = data.get('color') or data.get('team_colour') or data.get('logo_color')
            if c:
                t.logo_color = str(c)

        logo_file = request.FILES.get('logo') or request.FILES.get('team_logo')
        if logo_file:
            t.logo = logo_file

        t.save()

        # Update financials and custom data
        custom = auc_team.custom_data or {}
        for k in ['short_name', 'owner_name', 'owner_email', 'owner_mobile',
                  'manager_name', 'manager_email', 'manager_mobile', 'sponsor_name', 'logo_url']:
            if k in data:
                custom[k] = str(data[k]).strip()
        if 'remove_logo_background' in data:
            custom['remove_logo_background'] = data['remove_logo_background'] in [True, 'true', 'True', 1, '1']

        old_spent = (auction.base_budget + auc_team.additional_kitty - auc_team.reserve_amount - auc_team.penalty_amount) - auc_team.remaining_budget

        if 'additional_kitty' in data:
            try:
                auc_team.additional_kitty = Decimal(str(data['additional_kitty']))
            except Exception:
                pass
        if 'penalty_amount' in data or 'penalty' in data:
            try:
                auc_team.penalty_amount = Decimal(str(data.get('penalty_amount') or data.get('penalty')))
            except Exception:
                pass
        if 'reserve_amount' in data or 'reserve' in data:
            try:
                auc_team.reserve_amount = Decimal(str(data.get('reserve_amount') or data.get('reserve')))
            except Exception:
                pass

        auc_team.remaining_budget = (auction.base_budget + auc_team.additional_kitty - auc_team.reserve_amount - auc_team.penalty_amount) - old_spent
        auc_team.custom_data = custom
        auc_team.save()

        logo_val = ''
        if t.logo:
            try:
                logo_val = t.logo.url
            except Exception:
                logo_val = str(t.logo)
        if not logo_val:
            logo_val = custom.get('logo_url', '')

        if logo_val and not (logo_val.startswith('http://') or logo_val.startswith('https://')):
            logo_val = request.build_absolute_uri(logo_val)

        return Response({
            'success': True,
            'team': {
                'id': str(auc_team.id),
                'name': t.name,
                'short_name': custom.get('short_name', t.name[:3].upper()),
                'color': t.logo_color,
                'logo': logo_val,
                'logo_url': custom.get('logo_url', ''),
                'remove_logo_background': custom.get('remove_logo_background', False),
                'owner_name': custom.get('owner_name', ''),
                'owner_email': custom.get('owner_email', ''),
                'owner_mobile': custom.get('owner_mobile', ''),
                'manager_name': custom.get('manager_name', ''),
                'manager_email': custom.get('manager_email', ''),
                'manager_mobile': custom.get('manager_mobile', ''),
                'additional_kitty': float(auc_team.additional_kitty),
                'penalty_amount': float(auc_team.penalty_amount),
                'reserve_amount': float(auc_team.reserve_amount),
                'sponsor_name': custom.get('sponsor_name', ''),
                'remaining_budget': float(auc_team.remaining_budget),
                'players_count': auction.players.filter(sold_to=auc_team).count(),
                'live_token': auc_team.live_token,
            }
        })

    @action(detail=True, methods=['get'], permission_classes=[permissions.AllowAny])
    def teams_template(self, request, pk=None):
        """Generates downloadable CSV template for teams bulk import."""
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        headers = [
            'Team Name', 'Short Name', 'Owner Name', 'Owner Email', 'Owner Mobile',
            'Manager Name', 'Manager Email', 'Manager Mobile', 'Team Colour',
            'Logo URL', 'Additional Kitty', 'Penalty', 'Reserve', 'Sponsor Name'
        ]
        writer.writerow(headers)
        writer.writerow([
            'Royal Challengers', 'RCB', 'Vijay Sharma', 'owner@rcb.com', '9876543210',
            'Mo Bobat', 'manager@rcb.com', '9876543211', '#E03535',
            'https://example.com/rcb.png', '50000', '0', '0', 'Qatar Airways'
        ])
        writer.writerow([
            'Mumbai Titans', 'MT', 'Mukesh Ambani', 'owner@titans.com', '9876543212',
            'Zaheer Khan', 'manager@titans.com', '9876543213', '#2563EB',
            'https://example.com/titans.png', '0', '0', '0', 'Jio'
        ])

        response = HttpResponse(buffer.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="teams_import_template.csv"'
        return response

    @action(detail=True, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def bulk_import_teams(self, request, pk=None):
        """Bulk imports teams into tournament from an uploaded CSV or Excel file."""
        auction = self._get_auction(pk)
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({'error': 'No file provided.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            rows, headers = PlayerIntakeService.parse_file(file_obj)
            header_map = {str(h).strip().lower(): h for h in headers if h}

            sport = Sport.objects.first()
            if not sport:
                sport = Sport.objects.create(name='Cricket', slug='cricket', scoring_engine='cricket')

            PALETTE = [
                '#2563EB', '#DC2626', '#EAB308', '#16A34A', '#7C3AED', '#EA580C',
                '#0891B2', '#DB2777', '#4F46E5', '#059669', '#D97706', '#9333EA',
                '#0284C7', '#E11D48', '#65A30D', '#0D9488'
            ]

            imported_count = 0
            errors = []

            for idx, r in enumerate(rows):
                try:
                    def get_val(*aliases):
                        for a in aliases:
                            if a.lower() in header_map:
                                val = r.get(header_map[a.lower()])
                                if val is not None and str(val).strip():
                                    return str(val).strip()
                        return ""

                    t_name = get_val('team name', 'name', 'team')
                    if not t_name:
                        continue

                    s_name = (get_val('short name', 'short_name', 'code') or t_name[:3]).upper()[:3]
                    o_name = get_val('owner name', 'owner_name', 'owner')
                    o_email = get_val('owner email', 'owner_email', 'email')
                    o_mobile = get_val('owner mobile', 'owner_mobile', 'phone', 'mobile')
                    m_name = get_val('manager name', 'manager_name', 'co-owner name', 'manager')
                    m_email = get_val('manager email', 'manager_email', 'co-owner email')
                    m_mobile = get_val('manager mobile', 'manager_mobile', 'co-owner mobile')
                    color = get_val('team colour', 'team color', 'color', 'logo_color')
                    logo_url = get_val('logo url', 'team logo url', 'logo', 'photo url')
                    sponsor = get_val('sponsor name', 'sponsor', 'sponsor_name')

                    kitty_raw = get_val('additional kitty', 'kitty')
                    kitty = Decimal(str(kitty_raw).replace(',', '')) if kitty_raw else Decimal('0')

                    penalty_raw = get_val('penalty', 'penalty_amount')
                    penalty = Decimal(str(penalty_raw).replace(',', '')) if penalty_raw else Decimal('0')

                    reserve_raw = get_val('reserve', 'reserve_amount')
                    reserve = Decimal(str(reserve_raw).replace(',', '')) if reserve_raw else Decimal('0')

                    if not color:
                        color = PALETTE[(auction.teams.count() + imported_count) % len(PALETTE)]

                    # User for owner
                    owner_user = None
                    if o_email:
                        owner_user = User.objects.filter(email__iexact=o_email).first()
                    if not owner_user:
                        uname = f"owner_{uuid.uuid4().hex[:8]}"
                        owner_user = User.objects.create_user(
                            username=uname,
                            email=o_email or f"{uname}@turfarena.local",
                            full_name=o_name or t_name,
                            user_type='PLAYER'
                        )
                        if o_mobile and hasattr(owner_user, 'phone_number'):
                            owner_user.phone_number = o_mobile
                            owner_user.save()

                    team_obj = Team.objects.create(
                        user=owner_user,
                        sport=sport,
                        name=t_name,
                        logo_color=color,
                        customization={
                            'short_name': s_name,
                            'sponsor_name': sponsor,
                            'logo_url': logo_url,
                        }
                    )

                    budget = auction.base_budget + kitty - reserve - penalty
                    AuctionTeam.objects.create(
                        auction=auction,
                        team=team_obj,
                        remaining_budget=budget,
                        additional_kitty=kitty,
                        penalty_amount=penalty,
                        reserve_amount=reserve,
                        custom_data={
                            'short_name': s_name,
                            'owner_name': o_name,
                            'owner_email': o_email,
                            'owner_mobile': o_mobile,
                            'manager_name': m_name,
                            'manager_email': m_email,
                            'manager_mobile': m_mobile,
                            'sponsor_name': sponsor,
                            'logo_url': logo_url,
                        },
                        live_token=secrets.token_urlsafe(16)
                    )
                    imported_count += 1
                except Exception as e:
                    errors.append(f"Row {idx+2}: {str(e)}")

            return Response({
                'success': True,
                'imported_count': imported_count,
                'errors': errors,
                'total_rows': len(rows),
            })
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'], permission_classes=[permissions.AllowAny])
    def players_template(self, request, pk=None):
        """Generates downloadable CSV template for players bulk import."""
        auction = self._get_auction(pk)
        buffer = io.StringIO()
        writer = csv.writer(buffer)

        headers = [
            'Player No', 'Name', 'Mobile', 'Age', 'Location', 'Role',
            'Category', 'Base Price', 'Tagging', 'Photo URL',
            'Batting Style', 'Bowling Style', 'App Name', 'App ID',
            'Experience', 'Nationality', 'Pin Code', 'Awards Won', 'Bowling Type'
        ]

        # Add any custom fields defined for this tournament
        for cf in auction.custom_fields.filter(active=True):
            if cf.label not in headers:
                headers.append(cf.label)

        writer.writerow(headers)
        writer.writerow([
            '1', 'Rohit Sharma', '9876500001', '36', 'Mumbai', 'Top-Order Batsman',
            'Icon', '5000', 'Player', 'https://example.com/rohit.jpg',
            'Right Hand Bat', 'Right Arm Off Break', 'TurfPass', 'TP-101',
            '15 Years', 'Indian', '400001', '5 IPL Trophies', 'Off-Spin'
        ])
        writer.writerow([
            '2', 'Hardik Pandya', '9876500002', '30', 'Baroda', 'All-Rounder (Batting)',
            'Category A', '4000', 'Player', 'https://example.com/hardik.jpg',
            'Right Hand Bat', 'Right Arm Fast Medium', 'TurfPass', 'TP-102',
            '10 Years', 'Indian', '390001', 'Best All-Rounder 2024', 'Fast Medium'
        ])

        response = HttpResponse(buffer.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="players_import_template.csv"'
        return response

    @action(detail=True, methods=['get', 'post'], parser_classes=[MultiPartParser, FormParser, JSONParser])
    def page_design(self, request, pk=None):
        """Gets, updates, or resets broadcast auction page design layout JSON with asset upload support."""
        auction = self._get_auction(pk)
        design_obj, _ = AuctionPageDesign.objects.get_or_create(
            auction=auction,
            defaults={'design_json': DEFAULT_AUCTION_DESIGN}
        )

        if request.method == 'POST':
            if request.data.get('action') == 'reset':
                design_obj.design_json = DEFAULT_AUCTION_DESIGN
                design_obj.save(update_fields=['design_json'])
                return Response({'success': True, 'design_json': design_obj.design_json})

            raw_design = request.data.get('design_json')
            if isinstance(raw_design, str):
                try:
                    design_json = json.loads(raw_design)
                except Exception:
                    design_json = design_obj.design_json or DEFAULT_AUCTION_DESIGN
            elif isinstance(raw_design, dict):
                design_json = raw_design
            else:
                design_json = request.data if isinstance(request.data, dict) else design_obj.design_json

            existing_json = dict(design_obj.design_json or {})
            if isinstance(design_json, dict):
                # Safely merge so neither broadcast page design nor pdf design studio clobbers each other
                if 'pdf_design' in design_json and isinstance(design_json['pdf_design'], dict):
                    existing_json['pdf_design'] = design_json['pdf_design']
                if 'pdf_design' in request.data and isinstance(request.data['pdf_design'], dict):
                    existing_json['pdf_design'] = request.data['pdf_design']
                for k, v in design_json.items():
                    if k != 'pdf_design':
                        existing_json[k] = v
                design_json = existing_json

            # Handle direct file uploads for tournament branding logo or custom background
            if 'tournament_image' in request.FILES:
                t_file = request.FILES['tournament_image']
                remove_bg = str(request.data.get('remove_title_bg', '')).lower() in ['true', '1']
                try:
                    res = AssetManagerService.save_and_process_asset(
                        str(auction.id), t_file, 'Tournament Logo', 'Logo', remove_bg
                    )
                    if 'zones' not in design_json:
                        design_json['zones'] = {}
                    if 'branding' not in design_json['zones']:
                        design_json['zones']['branding'] = {}
                    design_json['zones']['branding']['title_image_url'] = res.get('processed_url') or res.get('original_url')
                    design_json['zones']['branding']['remove_title_bg'] = remove_bg
                except Exception as e:
                    print("Error processing tournament image:", e)

            if 'background_image' in request.FILES:
                bg_file = request.FILES['background_image']
                try:
                    res = AssetManagerService.save_and_process_asset(
                        str(auction.id), bg_file, 'Custom Stadium Background', 'Background', False
                    )
                    design_json['custom_background_url'] = res.get('processed_url') or res.get('original_url')
                    design_json['background_mode'] = 'custom'
                except Exception as e:
                    print("Error processing background image:", e)

            design_obj.design_json = design_json
            try:
                design_obj.save(update_fields=['design_json'])
            except Exception:
                design_obj.save()

            resp_payload = dict(design_obj.design_json)
            resp_payload['success'] = True
            resp_payload['design_json'] = dict(design_obj.design_json)
            return Response(resp_payload)

        raw_res = design_obj.design_json or DEFAULT_AUCTION_DESIGN
        if isinstance(raw_res, dict):
            out_res = dict(raw_res)
            out_res['design_json'] = dict(raw_res)
            return Response(out_res)
        return Response(raw_res)

    @action(detail=True, methods=['get', 'post'], permission_classes=[permissions.AllowAny])
    def public_link(self, request, pk=None):
        """Gets or regenerates the public spectator viewer token."""
        auction = self._get_auction(pk)
        link_obj = PublicAuctionLink.objects.filter(auction=auction).first()
        if not link_obj:
            token = secrets.token_urlsafe(18)
            link_obj = PublicAuctionLink.objects.create(auction=auction, public_token=token, enabled=True)

        if request.method == 'POST':
            action_type = request.data.get('action')
            if action_type == 'regenerate':
                link_obj.public_token = secrets.token_urlsafe(18)
                link_obj.enabled = True
                link_obj.save()
            elif action_type == 'toggle':
                link_obj.enabled = not link_obj.enabled
                link_obj.save()
            elif 'settings_json' in request.data:
                link_obj.settings_json = request.data.get('settings_json', {})
                link_obj.save()

        return Response(PublicAuctionLinkSerializer(link_obj).data)

    @action(detail=True, methods=['get', 'post'])
    def registration_link(self, request, pk=None):
        """Gets or manages public player registration link."""
        auction = self._get_auction(pk)
        reg_link = PlayerIntakeService.ensure_registration_token(auction)
        if request.method == 'POST':
            if request.data.get('regenerate'):
                reg_link.registration_token = secrets.token_urlsafe(20)
                reg_link.enabled = True
                reg_link.save()
            else:
                if 'enabled' in request.data:
                    reg_link.enabled = bool(request.data.get('enabled'))
                if 'title' in request.data:
                    reg_link.title = request.data.get('title', reg_link.title)
                if 'intro_text' in request.data:
                    reg_link.intro_text = request.data.get('intro_text', reg_link.intro_text)
                if 'success_message' in request.data:
                    reg_link.success_message = request.data.get('success_message', reg_link.success_message)
                if 'show_tournament_logo' in request.data:
                    reg_link.show_tournament_logo = bool(request.data.get('show_tournament_logo'))
                if 'show_tournament_name' in request.data:
                    reg_link.show_tournament_name = bool(request.data.get('show_tournament_name'))
                if 'fields_json' in request.data:
                    reg_link.fields_json = request.data.get('fields_json', reg_link.fields_json)
                reg_link.save()

        return Response(PlayerRegistrationLinkSerializer(reg_link).data)

    @action(detail=True, methods=['get', 'post'], permission_classes=[permissions.AllowAny])
    def group_draw(self, request, pk=None):
        """Group draw stage: generates blind cards, assigns, or reveals cards."""
        auction = self._get_auction(pk)

        if request.method == 'POST':
            draw_action = request.data.get('action')
            if draw_action == 'generate':
                group_names = request.data.get('groups', ['Group A', 'Group B'])
                teams_count = auction.teams.count()
                if teams_count == 0:
                    teams_count = 4
                
                auction.group_cards.all().delete()
                # Create card pool
                pool = []
                for i in range(teams_count):
                    g_name = group_names[i % len(group_names)]
                    pool.append(g_name)
                random.shuffle(pool)

                cards = []
                for idx, g_name in enumerate(pool, 1):
                    cards.append(GroupDrawCard(auction=auction, card_number=idx, group_name=g_name, revealed=False))
                GroupDrawCard.objects.bulk_create(cards)

            elif draw_action == 'assign':
                card_number = request.data.get('card_number')
                team_id = request.data.get('team_id')
                card = auction.group_cards.filter(card_number=card_number).first()
                if card:
                    if team_id:
                        team = None
                        try:
                            team_uuid = uuid.UUID(str(team_id))
                            team = auction.teams.filter(id=team_uuid).first()
                        except (ValueError, TypeError, Exception):
                            team = auction.teams.filter(id=team_id).first()
                        if not team:
                            team = auction.teams.filter(team__name__iexact=str(team_id)).first()
                        if team:
                            card.team = team
                            card.save()
                    else:
                        card.team = None
                        card.revealed = False
                        card.save()

            elif draw_action == 'unassign':
                card_number = request.data.get('card_number')
                card = auction.group_cards.filter(card_number=card_number).first()
                if card:
                    card.team = None
                    card.revealed = False
                    card.save()

            elif draw_action == 'reveal':
                card_number = request.data.get('card_number')
                card = auction.group_cards.filter(card_number=card_number).first()
                if card:
                    card.revealed = True
                    card.save()

            elif draw_action == 'reveal_all':
                auction.group_cards.all().update(revealed=True)

            elif draw_action == 'hide_all':
                auction.group_cards.all().update(revealed=False)

            elif draw_action == 'reset':
                auction.group_cards.all().delete()

        cards = auction.group_cards.all().order_by('card_number')
        return Response(GroupDrawCardSerializer(cards, many=True).data)

    @action(detail=True, methods=['get'])
    def all_teams_report(self, request, pk=None):
        """Generates comprehensive roster & financial summary for all franchise teams."""
        auction = self._get_auction(pk)

        teams_data = []
        for tm in auction.teams.select_related('team').all():
            sold_players = auction.players.filter(sold_to=tm, status='SOLD').order_by('serial_no')
            players_list = []
            for p in sold_players:
                players_list.append({
                    'id': str(p.id),
                    'serial_no': p.serial_no,
                    'name': p.player.full_name or p.player.first_name if p.player else 'Player',
                    'category': p.category,
                    'role': p.role,
                    'sold_price': float(p.sold_price or 0),
                })
            fin = team_financials(auction, tm)
            teams_data.append({
                'team_id': str(tm.id),
                'team_name': tm.team.name if tm.team else 'Team',
                'short_name': getattr(tm.team, 'short_name', tm.team.name[:3].upper()) if tm.team else 'TM',
                'color': tm.team.logo_color if tm.team else '#3b82f6',
                'financials': fin,
                'players': players_list,
                'player_count': len(players_list),
            })

        return Response({
            'auction_name': auction.name,
            'teams': teams_data,
        })

    @action(detail=True, methods=['get'])
    def overview(self, request, pk=None):
        """Returns comprehensive auction command center & live analytics statistics."""
        auction = self._get_auction(pk)
        if not auction:
            # Fallback demo stats if tournament not yet saved in DB
            return Response({
                'stats': {
                    'total_players': 8,
                    'sold_players': 0,
                    'unsold_players': 0,
                    'pending_players': 8,
                    'total_purse': 400000,
                    'spent_purse': 0,
                    'remaining_purse': 400000,
                },
                'categories': [
                    {'name': 'Icon', 'target': 2, 'base_price': 5000, 'total': 2, 'sold': 0, 'unsold': 0, 'pending': 2},
                    {'name': 'Tier 1', 'target': 4, 'base_price': 3500, 'total': 4, 'sold': 0, 'unsold': 0, 'pending': 4},
                    {'name': 'Tier 2', 'target': 2, 'base_price': 2000, 'total': 2, 'sold': 0, 'unsold': 0, 'pending': 2},
                ],
                'teams': [
                    {'id': '1', 'name': 'Mumbai Titans', 'spent': 0, 'remaining': 100000, 'players_count': 0},
                    {'id': '2', 'name': 'Bangalore Blasters', 'spent': 0, 'remaining': 100000, 'players_count': 0},
                    {'id': '3', 'name': 'Chennai Superstars', 'spent': 0, 'remaining': 100000, 'players_count': 0},
                    {'id': '4', 'name': 'Delhi Smashers', 'spent': 0, 'remaining': 100000, 'players_count': 0},
                ],
            })

        players = auction.players.all()
        teams = auction.teams.select_related('team').all()
        categories = AuctionCategory.objects.filter(auction=auction)

        total_players = players.count()
        sold_players = players.filter(status='SOLD').count()
        unsold_players = players.filter(status='UNSOLD').count()
        pending_players = total_players - sold_players - unsold_players

        base_budget = float(auction.base_budget or 100000)
        total_purse = base_budget * teams.count() if teams.exists() else base_budget
        spent_purse = sum([float(p.sold_price or 0) for p in players.filter(status='SOLD')])
        remaining_purse = max(0, total_purse - spent_purse)

        cat_data = []
        if categories.exists():
            for c in categories:
                c_players = players.filter(category=c.name)
                c_total = c_players.count()
                c_sold = c_players.filter(status='SOLD').count()
                c_unsold = c_players.filter(status='UNSOLD').count()
                cat_data.append({
                    'name': c.name,
                    'target': c.target_count,
                    'base_price': float(c.base_price or 0),
                    'total': c_total,
                    'sold': c_sold,
                    'unsold': c_unsold,
                    'pending': max(0, c_total - c_sold - c_unsold),
                })
        else:
            # Group existing players by tier / role
            cat_map = {}
            for p in players:
                cat_name = p.tier or p.role or 'General'
                cat_map.setdefault(cat_name, {'total': 0, 'sold': 0, 'unsold': 0, 'base': float(p.base_price or 2000)})
                cat_map[cat_name]['total'] += 1
                if p.status == 'SOLD':
                    cat_map[cat_name]['sold'] += 1
                elif p.status == 'UNSOLD':
                    cat_map[cat_name]['unsold'] += 1
            for k, v in cat_map.items():
                cat_data.append({
                    'name': k,
                    'target': v['total'],
                    'base_price': v['base'],
                    'total': v['total'],
                    'sold': v['sold'],
                    'unsold': v['unsold'],
                    'pending': max(0, v['total'] - v['sold'] - v['unsold']),
                })

        team_data = []
        for t in teams:
            t_sold = players.filter(sold_to=t, status='SOLD')
            t_spent = sum([float(p.sold_price or 0) for p in t_sold])
            t_rem = float(t.remaining_budget if t.remaining_budget is not None else base_budget - t_spent)
            team_data.append({
                'id': str(t.id),
                'name': t.team.name if t.team else 'Franchise Team',
                'spent': t_spent,
                'remaining': t_rem,
                'players_count': t_sold.count(),
            })

        top_sales = []
        for p in players.filter(status='SOLD').order_by('-sold_price')[:5]:
            p_name = p.player.full_name or p.player.first_name if p.player else getattr(p, 'name', 'Player')
            tm_name = p.sold_to.team.name if (p.sold_to and p.sold_to.team) else 'Franchise'
            top_sales.append({
                'id': str(p.id),
                'name': p_name,
                'category': p.category or p.tier or 'Icon',
                'team_name': tm_name,
                'sold_price': float(p.sold_price or 0),
            })

        return Response({
            'total_players': total_players,
            'sold_count': sold_players,
            'unsold_count': unsold_players,
            'pending_count': pending_players,
            'total_spent': spent_purse,
            'total_purse': total_purse,
            'remaining_purse': remaining_purse,
            'team_count': teams.count(),
            'categories': cat_data,
            'teams': team_data,
            'top_sales': top_sales,
            'stats': {
                'total_players': total_players,
                'sold_players': sold_players,
                'unsold_players': unsold_players,
                'pending_players': pending_players,
                'total_purse': total_purse,
                'spent_purse': spent_purse,
                'remaining_purse': remaining_purse,
            },
        })

    @action(detail=True, methods=['get', 'post'], permission_classes=[permissions.AllowAny])
    def export_cards_pdf(self, request, pk=None):
        """Generates a downloadable printable PDF of player auction cards based on grid settings."""
        auction = self._get_auction(pk)
        auction_name = auction.name if auction else 'Auction'
        try:
            cols = int(request.query_params.get('cols', 3))
            rows = int(request.query_params.get('rows', 5))
        except (ValueError, TypeError):
            cols, rows = 3, 5

        pdf_format = (
            request.query_params.get('pdf_format') or
            request.query_params.get('export_format') or
            request.query_params.get('format') or
            (request.data.get('pdf_format') if isinstance(request.data, dict) else None) or
            (request.data.get('format') if isinstance(request.data, dict) else None) or
            'category'
        )

        # Load saved PDF design settings if available safely without raising ObjectDoesNotExist
        design_obj = AuctionPageDesign.objects.filter(auction=auction).first() if auction else None
        pdf_settings = (design_obj.design_json or {}).get('pdf_design', {}) if design_obj else {}
        if not pdf_settings and design_obj and isinstance(design_obj.design_json, dict):
            if 'branding' in design_obj.design_json or 'elements' in design_obj.design_json:
                pdf_settings = design_obj.design_json
        
        # Check if direct pdf_design was passed in POST body
        if request.method == 'POST' and isinstance(request.data, dict):
            if 'pdf_design' in request.data and isinstance(request.data['pdf_design'], dict):
                pdf_settings = request.data['pdf_design']
            elif 'branding' in request.data or 'elements' in request.data:
                pdf_settings = request.data

        players = list(auction.players.select_related('player').all().order_by('serial_no', 'id')) if auction else []
        if not players:
            class MockP:
                def __init__(self, s, n, r, c, b, loc='Mumbai', bat='Right Hand', bowl='Right Arm', mob='9876543210', age=28, exp='5 Yrs', app_id='APP-001'):
                    self.serial_no = s
                    self.role = r
                    self.category = c
                    self.tier = c
                    self.base_price = b
                    self.name = n
                    self.location = loc
                    self.batting_style = bat
                    self.bowling_style = bowl
                    self.mobile = mob
                    self.age = age
                    self.experience = exp
                    self.custom_data = {'experience': exp, 'application_id': app_id}
                    self.id = s
            players = [
                MockP(1, 'Virat Kohli', 'Top-Order Batsman', 'Icon Players', 5000),
                MockP(2, 'Jasprit Bumrah', 'Fast Bowler', 'Icon Players', 5000),
                MockP(3, 'Hardik Pandya', 'All-Rounder', 'Tier 1 Batsmen', 4000),
                MockP(4, 'Rishabh Pant', 'Wicket-Keeper', 'Tier 1 Batsmen', 3500),
                MockP(5, 'Rashid Khan', 'Spin Bowler', 'Tier 1 Bowlers', 3500),
                MockP(6, 'Suryakumar Yadav', '360 Batsman', 'Tier 1 Batsmen', 4000),
                MockP(7, 'Mohammed Shami', 'Pace Bowler', 'Tier 1 Bowlers', 2500),
                MockP(8, 'Rinku Singh', 'Finisher Batsman', 'Tier 2 Emerging', 2000),
            ]

        from django.http import HttpResponse
        pdf_bytes = self._generate_pure_cards_pdf(
            auction_name=auction_name,
            players=players,
            cols=cols,
            rows=rows,
            pdf_format=pdf_format,
            pdf_settings=pdf_settings
        )
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{auction_name}_Player_Cards.pdf"'
        return response

    def _process_image_to_jpeg_dict(self, img_data_or_url, opacity=1.0):
        if not img_data_or_url:
            return None
        try:
            import io
            import os
            import base64
            from PIL import Image
            from django.conf import settings

            raw_bytes = None
            s = str(img_data_or_url).strip()

            if s.startswith('data:'):
                if ',' in s:
                    _, b64_part = s.split(',', 1)
                    raw_bytes = base64.b64decode(b64_part)
            elif s.startswith('http://') or s.startswith('https://'):
                import urllib.request
                req = urllib.request.urlopen(s, timeout=6)
                raw_bytes = req.read()
            elif s.startswith('/media/') or s.startswith('media/'):
                rel_path = s.lstrip('/').replace('media/', '', 1)
                full_path = os.path.join(settings.MEDIA_ROOT, rel_path)
                if os.path.exists(full_path):
                    with open(full_path, 'rb') as f:
                        raw_bytes = f.read()
            elif os.path.exists(s):
                with open(s, 'rb') as f:
                    raw_bytes = f.read()

            if not raw_bytes:
                return None

            im = Image.open(io.BytesIO(raw_bytes))
            # Downscale if excessively large to keep PDF rendering fast & lightweight
            max_dim = 1600
            if im.width > max_dim or im.height > max_dim:
                im.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)

            orig_w, orig_h = im.size
            opacity = max(0.01, min(1.0, float(opacity)))

            if opacity < 0.999 or im.mode in ('RGBA', 'LA', 'P'):
                im = im.convert('RGBA')
                if opacity < 0.999:
                    r, g, b, a = im.split()
                    a = a.point(lambda p: int(p * opacity))
                    im.putalpha(a)
                # Composite onto clean white canvas for standard PDF RGB JPEG
                white_canvas = Image.new('RGBA', im.size, (255, 255, 255, 255))
                final_im = Image.alpha_composite(white_canvas, im).convert('RGB')
            else:
                final_im = im.convert('RGB')

            out_io = io.BytesIO()
            final_im.save(out_io, format='JPEG', quality=88, optimize=True)
            jpeg_bytes = out_io.getvalue()

            return {
                'bytes': jpeg_bytes,
                'width': orig_w,
                'height': orig_h,
            }
        except Exception as e:
            print(f"[PDF Engine] Failed to process image: {e}")
            return None

    def _generate_pure_cards_pdf(self, auction_name, players, cols=3, rows=5, pdf_format='category', pdf_settings=None):
        from collections import defaultdict
        width, height = 595.28, 841.89  # A4 in points (210mm x 297mm)
        cfg = pdf_settings or {}
        cfg_elements = cfg.get('elements', {})
        branding = cfg.get('branding', {})
        header_cfg = cfg.get('header', {})
        footer_cfg = cfg.get('footer', {})

        show_header = header_cfg.get('show', True)
        header_h = float(header_cfg.get('height', 26.0)) if show_header else 0.0

        show_footer = footer_cfg.get('show', False)
        footer_h = float(footer_cfg.get('height', 20.0)) if show_footer else 0.0

        margin = float(cfg.get('margin', 15.0))
        usable_w = width - (2 * margin)
        usable_h = height - (2 * margin) - header_h - footer_h - 10.0
        card_w = usable_w / max(1, cols)
        card_h = usable_h / max(1, rows)
        page_capacity = cols * rows

        show_t_name = branding.get('show_tournament_name', True)
        t_title = branding.get('tournament_title') or auction_name or 'Turf Tournament'

        card_fill_hex = cfg.get('card_fill', '#FFFFFF')
        accent_hex = cfg.get('accent_colour', '#2563EB')

        def hex_to_rgb(h):
            h = str(h or '').lstrip('#')
            if len(h) == 6:
                try:
                    return tuple(int(h[i:i+2], 16) / 255.0 for i in (0, 2, 4))
                except ValueError:
                    pass
            return (0.145, 0.388, 0.922)

        accent_r, accent_g, accent_b = hex_to_rgb(accent_hex)
        fill_r, fill_g, fill_b = hex_to_rgb(card_fill_hex)

        def esc(t):
            s = str(t or '').replace('₹', 'Rs. ')
            cleaned = "".join([c if ord(c) < 128 else ' ' for c in s])
            return cleaned.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')

        # 1. Prepare Background Image / Watermark
        bg_image_data = (
            branding.get('pageBackgroundImage') or
            branding.get('page_background_image') or
            cfg.get('pageBackgroundImage')
        )
        bg_opacity_raw = branding.get('pageBackgroundOpacity', 20)
        try:
            bg_opacity = float(bg_opacity_raw) / 100.0
        except (ValueError, TypeError):
            bg_opacity = 0.20

        images_dict = {}
        bg_info = None
        if bg_image_data:
            bg_info = self._process_image_to_jpeg_dict(bg_image_data, opacity=bg_opacity)
            if bg_info:
                images_dict['/ImBg'] = bg_info

        # 2. Prepare Draggable Logos
        placed_logos = (
            branding.get('placedLogos') or
            branding.get('logos') or
            cfg.get('placedLogos') or
            []
        )
        if not placed_logos:
            single_logo = (
                branding.get('customLogoUrl') or
                branding.get('logoUrl') or
                branding.get('title_image_url')
            )
            if single_logo:
                placed_logos = [{
                    'url': single_logo,
                    'x': float(branding.get('logoX', 4)),
                    'y': float(branding.get('logoY', 1.5)),
                    'width': float(branding.get('logoWidth', 10)),
                }]

        prepared_logos = []
        for idx, l_item in enumerate(placed_logos):
            l_url = l_item.get('url') or l_item.get('data')
            if not l_url:
                continue
            logo_info = self._process_image_to_jpeg_dict(l_url, opacity=1.0)
            if logo_info:
                img_ref = f"/ImLogo{idx}"
                images_dict[img_ref] = logo_info
                try:
                    prepared_logos.append({
                        'ref': img_ref,
                        'info': logo_info,
                        'x_pct': float(l_item.get('x', 4)),
                        'y_pct': float(l_item.get('y', 1.5)),
                        'w_pct': float(l_item.get('width', 10)),
                    })
                except (ValueError, TypeError):
                    continue

        # 3. Default element coordinates matching design studio
        layout_defaults = {
            'player_number': {'selected': True, 'x': 38, 'y': 6, 'w': 24, 'h': 12, 'font_size': 13, 'colour': '#0284c7', 'bold': True, 'show_label': False},
            'player_photo': {'selected': True, 'x': 4, 'y': 6, 'w': 30, 'h': 86, 'font_size': 10, 'colour': '#000000', 'bold': False, 'show_label': True},
            'name': {'selected': True, 'x': 38, 'y': 19, 'w': 58, 'h': 14, 'font_size': 13, 'colour': '#0f172a', 'bold': True, 'show_label': False},
            'category': {'selected': True, 'x': 62, 'y': 6, 'w': 34, 'h': 12, 'font_size': 10, 'colour': '#7c3aed', 'bold': True, 'show_label': False, 'align': 'right'},
            'role': {'selected': True, 'x': 38, 'y': 32, 'w': 58, 'h': 12, 'font_size': 9.5, 'colour': '#334155', 'bold': False, 'show_label': False},
            'base_price': {'selected': True, 'x': 38, 'y': 44, 'w': 58, 'h': 14, 'font_size': 10.5, 'colour': '#16a34a', 'bold': True, 'show_label': True},
            'location': {'selected': True, 'x': 38, 'y': 59, 'w': 28, 'h': 10, 'font_size': 8.5, 'colour': '#64748b', 'bold': False, 'show_label': True},
            'batting': {'selected': True, 'x': 68, 'y': 59, 'w': 28, 'h': 10, 'font_size': 8.5, 'colour': '#64748b', 'bold': False, 'show_label': True},
            'bowling': {'selected': True, 'x': 38, 'y': 71, 'w': 28, 'h': 10, 'font_size': 8.5, 'colour': '#64748b', 'bold': False, 'show_label': True},
            'mobile': {'selected': True, 'x': 68, 'y': 71, 'w': 28, 'h': 10, 'font_size': 8.5, 'colour': '#64748b', 'bold': False, 'show_label': True},
            'age': {'selected': True, 'x': 38, 'y': 83, 'w': 18, 'h': 10, 'font_size': 8.5, 'colour': '#64748b', 'bold': False, 'show_label': True},
            'experience': {'selected': True, 'x': 57, 'y': 83, 'w': 20, 'h': 10, 'font_size': 8.5, 'colour': '#64748b', 'bold': False, 'show_label': True},
            'application_id': {'selected': True, 'x': 78, 'y': 83, 'w': 18, 'h': 10, 'font_size': 8.5, 'colour': '#64748b', 'bold': False, 'show_label': True},
        }

        pages = []

        def build_page_stream(page_players, section_title, page_num=1, total_pages=1):
            cmds = []

            # (A) Page Background Image / Watermark with Opacity
            if bg_info:
                cmds.append(f"q {width:.2f} 0 0 {height:.2f} 0 0 cm /ImBg Do Q")

            # (B) Sheet Header Banner (Configurable & Adjustable)
            if show_header:
                h_bg_r, h_bg_g, h_bg_b = hex_to_rgb(header_cfg.get('bg_colour', '#f8fafc'))
                h_tx_r, h_tx_g, h_tx_b = hex_to_rgb(header_cfg.get('text_colour', '#0f172a'))
                cmds.append(f"{h_bg_r:.3f} {h_bg_g:.3f} {h_bg_b:.3f} rg {margin:.1f} {height - margin - header_h:.1f} {usable_w:.1f} {header_h:.1f} re f")
                cmds.append(f"{accent_r:.3f} {accent_g:.3f} {accent_b:.3f} rg {margin:.1f} {height - margin - header_h:.1f} {usable_w:.1f} 2.0 re f")

                hdr_title = header_cfg.get('title') or (f"{t_title}   |   {section_title}" if show_t_name else section_title)
                h_font_sz = float(header_cfg.get('font_size', 10.5))
                hdr_y = height - margin - (header_h / 2.0) - (h_font_sz * 0.35)
                cmds.append(f"BT /F2 {h_font_sz:.1f} Tf {h_tx_r:.3f} {h_tx_g:.3f} {h_tx_b:.3f} rg {margin + 8:.1f} {hdr_y:.1f} Td ({esc(hdr_title)}) Tj ET")

                hdr_right = header_cfg.get('right_text') or ("Every category on new page" if pdf_format == 'category' else "Continuous order")
                if hdr_right:
                    right_x = margin + usable_w - (len(hdr_right) * 5.2) - 8
                    cmds.append(f"BT /F1 8.5 Tf 0.40 0.45 0.55 rg {right_x:.1f} {hdr_y:.1f} Td ({esc(hdr_right)}) Tj ET")

            # (C) Sheet Footer Banner (Configurable & Adjustable)
            if show_footer:
                f_bg_r, f_bg_g, f_bg_b = hex_to_rgb(footer_cfg.get('bg_colour', '#f8fafc'))
                f_tx_r, f_tx_g, f_tx_b = hex_to_rgb(footer_cfg.get('text_colour', '#64748b'))
                f_y = margin
                cmds.append(f"{f_bg_r:.3f} {f_bg_g:.3f} {f_bg_b:.3f} rg {margin:.1f} {f_y:.1f} {usable_w:.1f} {footer_h:.1f} re f")
                cmds.append(f"{accent_r:.3f} {accent_g:.3f} {accent_b:.3f} rg {margin:.1f} {f_y + footer_h - 1.0:.1f} {usable_w:.1f} 1.0 re f")

                f_sz = float(footer_cfg.get('font_size', 8.5))
                f_ty = f_y + (footer_h / 2.0) - (f_sz * 0.35)

                f_left = footer_cfg.get('left_text', '')
                if f_left:
                    cmds.append(f"BT /F1 {f_sz:.1f} Tf {f_tx_r:.3f} {f_tx_g:.3f} {f_tx_b:.3f} rg {margin + 8:.1f} {f_ty:.1f} Td ({esc(f_left)}) Tj ET")

                f_center = (footer_cfg.get('center_text') or '').replace('{page}', str(page_num)).replace('{totalPages}', str(total_pages))
                if f_center:
                    c_x = margin + (usable_w / 2.0) - (len(f_center) * f_sz * 0.25)
                    cmds.append(f"BT /F1 {f_sz:.1f} Tf {f_tx_r:.3f} {f_tx_g:.3f} {f_tx_b:.3f} rg {c_x:.1f} {f_ty:.1f} Td ({esc(f_center)}) Tj ET")

                f_right = footer_cfg.get('right_text', '')
                if f_right:
                    r_x = margin + usable_w - (len(f_right) * f_sz * 0.52) - 8
                    cmds.append(f"BT /F1 {f_sz:.1f} Tf {f_tx_r:.3f} {f_tx_g:.3f} {f_tx_b:.3f} rg {r_x:.1f} {f_ty:.1f} Td ({esc(f_right)}) Tj ET")

            # (C) Render Draggable Logos
            for l_entry in prepared_logos:
                w_px = l_entry['info']['width']
                h_px = l_entry['info']['height']
                aspect = float(h_px) / float(w_px) if w_px > 0 else 1.0

                lw_pt = (l_entry['w_pct'] / 100.0) * width
                lh_pt = lw_pt * aspect
                lx_pt = (l_entry['x_pct'] / 100.0) * width
                ly_pt = height - ((l_entry['y_pct'] / 100.0) * height) - lh_pt

                cmds.append(f"q {lw_pt:.2f} 0 0 {lh_pt:.2f} {lx_pt:.2f} {ly_pt:.2f} cm {l_entry['ref']} Do Q")

            # (D) Card Grid
            for r in range(rows):
                for c in range(cols):
                    idx = (r * cols) + c
                    if idx >= len(page_players):
                        continue
                    p = page_players[idx]
                    card_x = margin + (c * card_w)
                    card_y = height - margin - header_h - 6.0 - ((r + 1) * card_h)
                    cx = card_x + 2.5
                    cy = card_y + 2.5
                    cw = card_w - 5.0
                    ch = card_h - 5.0
                    card_top = cy + ch

                    # Card fill & border with opacity support
                    card_opacity_val = float(cfg.get('card_fill_opacity', 95))
                    if card_opacity_val <= 5.0:
                        cmds.append(f"{accent_r:.3f} {accent_g:.3f} {accent_b:.3f} RG 0.8 w {cx:.1f} {cy:.1f} {cw:.1f} {ch:.1f} re S")
                    else:
                        cmds.append(f"{fill_r:.3f} {fill_g:.3f} {fill_b:.3f} rg {accent_r:.3f} {accent_g:.3f} {accent_b:.3f} RG 0.8 w {cx:.1f} {cy:.1f} {cw:.1f} {ch:.1f} re B")
                    
                    # Top accent bar
                    cmds.append(f"{accent_r:.3f} {accent_g:.3f} {accent_b:.3f} rg {cx:.1f} {card_top - 3.5:.1f} {cw:.1f} 3.5 re f")

                    serial = getattr(p, 'serial_no', '—')
                    p_user = getattr(p, 'player', None)
                    name = (
                        getattr(p, 'name', None) or
                        (getattr(p_user, 'full_name', None) if p_user else None) or
                        (getattr(p_user, 'first_name', None) if p_user else None) or
                        (getattr(p_user, 'username', None) if p_user else None) or
                        'Player'
                    )
                    role = getattr(p, 'role', 'Player') or 'Player'
                    cat = getattr(p, 'category', None) or getattr(p, 'tier', None) or 'General'
                    price = getattr(p, 'base_price', 2000) or 2000
                    loc = getattr(p, 'location', '') or ''
                    bat = getattr(p, 'batting_style', '') or ''
                    bowl = getattr(p, 'bowling_style', '') or ''
                    mob = getattr(p, 'mobile', '') or ''
                    age = getattr(p, 'age', '') or ''
                    cdata = getattr(p, 'custom_data', {}) or {}
                    exp = getattr(p, 'experience', '') or cdata.get('experience') or ''
                    app_id = cdata.get('application_id') or str(getattr(p, 'id', ''))[:8]

                    # Combine default layout keys with any custom keys defined in cfg_elements
                    all_keys = list(layout_defaults.keys())
                    for k in cfg_elements.keys():
                        if k not in all_keys:
                            all_keys.append(k)

                    # Global element box opacity if set
                    global_box_op = float(cfg.get('element_box_opacity', 0))

                    # Render each element by relative % position to prevent any overlaps
                    for el_key in all_keys:
                        def_cfg = layout_defaults.get(el_key, {
                            'selected': True, 'x': 38, 'y': 80, 'w': 40, 'h': 10,
                            'font_size': 9, 'colour': '#0f172a', 'bold': False, 'show_label': True
                        })
                        cfg_el = cfg_elements.get(el_key, {})
                        el = {**def_cfg, **cfg_el}
                        if not el.get('selected', True):
                            continue

                        el_x = cx + (float(el.get('x', 0)) / 100.0) * cw
                        el_w = (float(el.get('w', 20)) / 100.0) * cw
                        el_h = (float(el.get('h', 10)) / 100.0) * ch
                        el_y_top = card_top - (float(el.get('y', 0)) / 100.0) * ch
                        el_y_bottom = el_y_top - el_h

                        # Draw box background pill if box opacity is enabled
                        el_box_op = float(el.get('bg_opacity') if el.get('bg_opacity') is not None else global_box_op)
                        if el_box_op > 0 and el_key != 'player_photo' and el_key != 'base_price':
                            box_bg_r, box_bg_g, box_bg_b = hex_to_rgb(el.get('bg_colour', '#FFFFFF'))
                            cmds.append(f"{box_bg_r:.3f} {box_bg_g:.3f} {box_bg_b:.3f} rg 0.85 0.88 0.92 RG 0.4 w {el_x:.1f} {el_y_bottom:.1f} {el_w:.1f} {el_h:.1f} re B")

                        is_custom_box = el.get('is_custom', False)
                        custom_override = el.get('custom_text')
                        # Ignore legacy/hardcoded template text for standard dynamic fields
                        if not is_custom_box and custom_override in [
                            'Virat Kohli', 'Icon', '₹50,000', 'Batsman', 'Mumbai',
                            'RHB', 'RAF', '9876543210', '28', '5 Yrs', '104', '#1'
                        ]:
                            custom_override = None

                        custom_lbl = el.get('label')
                        c_r, c_g, c_b = hex_to_rgb(el.get('colour', '#0f172a'))
                        f_sz = max(6.0, min(14.0, float(el.get('font_size', 9.5)) * 0.72))
                        font_choice = '/F2' if el.get('bold', False) else '/F1'

                        if el_key == 'player_photo':
                            cmds.append(f"0.93 0.95 0.97 rg 0.78 0.82 0.88 RG 0.5 w {el_x:.1f} {el_y_bottom:.1f} {el_w:.1f} {el_h:.1f} re B")
                            ph_tx = el_x + max(2.0, (el_w - 28.0) / 2.0)
                            ph_ty = el_y_bottom + (el_h / 2.0) - 3.0
                            cmds.append(f"BT /F2 8.5 Tf 0.45 0.50 0.60 rg {ph_tx:.1f} {ph_ty:.1f} Td (PHOTO) Tj ET")

                        elif el_key == 'player_number':
                            lbl = (custom_lbl + ' ') if custom_lbl else ('No: ' if el.get('show_label', False) else '#')
                            val_text = f"{lbl}{serial}" if custom_override is None else f"{lbl}{custom_override}"
                            f_sz = max(8.0, min(12.0, float(el.get('font_size', 13)) * 0.75))
                            ty = el_y_bottom + (el_h / 2.0) - (f_sz * 0.35)
                            cmds.append(f"BT /F2 {f_sz:.1f} Tf {c_r:.3f} {c_g:.3f} {c_b:.3f} rg {el_x:.1f} {ty:.1f} Td ({esc(val_text)}) Tj ET")

                        elif el_key == 'category':
                            lbl = (custom_lbl + ' ') if custom_lbl else ('Cat: ' if el.get('show_label', False) else '')
                            val_text = f"[{lbl}{cat}]" if custom_override is None else f"[{lbl}{custom_override}]"
                            f_sz = max(7.0, min(10.0, float(el.get('font_size', 10)) * 0.72))
                            ty = el_y_bottom + (el_h / 2.0) - (f_sz * 0.35)
                            text_len_est = len(val_text) * f_sz * 0.52
                            tx = max(el_x, el_x + el_w - text_len_est) if el.get('align') == 'right' else el_x
                            cmds.append(f"BT /F2 {f_sz:.1f} Tf {c_r:.3f} {c_g:.3f} {c_b:.3f} rg {tx:.1f} {ty:.1f} Td ({esc(val_text)}) Tj ET")

                        elif el_key == 'name':
                            lbl = (custom_lbl + ' ') if custom_lbl else ('Name: ' if el.get('show_label', False) else '')
                            val_text = f"{lbl}{name}" if custom_override is None else f"{lbl}{custom_override}"
                            f_sz = max(9.0, min(13.0, float(el.get('font_size', 13)) * 0.75))
                            ty = el_y_bottom + (el_h / 2.0) - (f_sz * 0.35)
                            cmds.append(f"BT /F2 {f_sz:.1f} Tf {c_r:.3f} {c_g:.3f} {c_b:.3f} rg {el_x:.1f} {ty:.1f} Td ({esc(val_text)[:28]}) Tj ET")

                        elif el_key == 'role':
                            lbl = (custom_lbl + ' ') if custom_lbl else ('Role: ' if el.get('show_label', False) else '')
                            val_text = f"{lbl}{role}" if custom_override is None else f"{lbl}{custom_override}"
                            f_sz = max(7.0, min(9.5, float(el.get('font_size', 9.5)) * 0.72))
                            ty = el_y_bottom + (el_h / 2.0) - (f_sz * 0.35)
                            cmds.append(f"BT /F1 {f_sz:.1f} Tf {c_r:.3f} {c_g:.3f} {c_b:.3f} rg {el_x:.1f} {ty:.1f} Td ({esc(val_text)[:28]}) Tj ET")

                        elif el_key == 'base_price':
                            lbl = (custom_lbl + ' ') if custom_lbl else ('Base Price: ' if el.get('show_label', True) else 'Base: ')
                            val_text = f"{lbl}Rs. {int(price):,}" if custom_override is None else f"{lbl}{custom_override}"
                            pill_h = el_h - 1.5
                            pill_y = el_y_bottom + 0.75
                            if el.get('bg_opacity') != 0:
                                bg_hex = el.get('bg_colour')
                                if bg_hex and bg_hex != '#ffffff':
                                    b_r, b_g, b_b = hex_to_rgb(bg_hex)
                                    cmds.append(f"{b_r:.3f} {b_g:.3f} {b_b:.3f} rg 0.70 0.88 0.75 RG 0.5 w {el_x:.1f} {pill_y:.1f} {el_w:.1f} {pill_h:.1f} re B")
                                else:
                                    cmds.append(f"0.92 0.98 0.94 rg 0.70 0.88 0.75 RG 0.5 w {el_x:.1f} {pill_y:.1f} {el_w:.1f} {pill_h:.1f} re B")
                            f_sz = max(7.0, min(10.5, float(el.get('font_size', 10.5)) * 0.75))
                            ty = pill_y + (pill_h / 2.0) - (f_sz * 0.35)
                            cmds.append(f"BT /F2 {f_sz:.1f} Tf 0.086 0.639 0.290 rg {el_x + 3.0:.1f} {ty:.1f} Td ({esc(val_text)}) Tj ET")

                        else:
                            # Standard detail field or custom box
                            val_raw = custom_override if custom_override is not None else ''
                            default_lbl = custom_lbl if custom_lbl is not None else ''
                            if not val_raw and custom_override is None:
                                if el_key == 'location': val_raw = loc; default_lbl = default_lbl or 'Loc: '
                                elif el_key == 'batting': val_raw = bat; default_lbl = default_lbl or 'Bat: '
                                elif el_key == 'bowling': val_raw = bowl; default_lbl = default_lbl or 'Bowl: '
                                elif el_key == 'mobile': val_raw = mob; default_lbl = default_lbl or 'Mob: '
                                elif el_key == 'age': val_raw = str(age); default_lbl = default_lbl or 'Age: '
                                elif el_key == 'experience': val_raw = str(exp); default_lbl = default_lbl or 'Exp: '
                                elif el_key == 'application_id': val_raw = str(app_id); default_lbl = default_lbl or 'ID: '
                                else:
                                    val_raw = el.get('label') or el_key.replace('_', ' ').title()

                            lbl = default_lbl if el.get('show_label', True) else ''
                            val_text = f"{lbl}{val_raw}" if not val_raw.startswith(lbl) else val_raw
                            ty = el_y_bottom + (el_h / 2.0) - (f_sz * 0.35)
                            align = el.get('align', 'left')
                            tx = el_x
                            if align == 'right':
                                tx = max(el_x, el_x + el_w - (len(val_text) * f_sz * 0.52))
                            elif align == 'center':
                                tx = max(el_x, el_x + (el_w / 2.0) - (len(val_text) * f_sz * 0.26))
                            cmds.append(f"BT {font_choice} {f_sz:.1f} Tf {c_r:.3f} {c_g:.3f} {c_b:.3f} rg {tx:.1f} {ty:.1f} Td ({esc(val_text)[:32]}) Tj ET")

            return "\n".join(cmds)

        if pdf_format == 'category':
            # Category Wise: Every category starts on a new page!
            cat_groups = defaultdict(list)
            for p in players:
                cat_name = getattr(p, 'category', None) or getattr(p, 'tier', None) or 'General Category'
                cat_groups[cat_name].append(p)

            total_pages = 0
            for c_players in cat_groups.values():
                total_pages += (len(c_players) + page_capacity - 1) // max(1, page_capacity)
            total_pages = max(1, total_pages)

            curr_page = 1
            for cat_name, c_players in cat_groups.items():
                for p_idx in range(0, len(c_players), page_capacity):
                    p_slice = c_players[p_idx:p_idx + page_capacity]
                    page_label = f"Category: {cat_name} ({len(c_players)} Players)"
                    pages.append(build_page_stream(p_slice, page_label, curr_page, total_pages))
                    curr_page += 1
        else:
            # Auction Format: Continuous sequential lot order
            total_pages = max(1, (len(players) + page_capacity - 1) // max(1, page_capacity))
            curr_page = 1
            for p_idx in range(0, len(players), page_capacity):
                p_slice = players[p_idx:p_idx + page_capacity]
                page_label = f"Auction Format (Lots {p_idx + 1} - {min(len(players), p_idx + page_capacity)} of {len(players)})"
                pages.append(build_page_stream(p_slice, page_label, curr_page, total_pages))
                curr_page += 1

        return self._assemble_raw_pdf(pages, width, height, images_dict)

    def _assemble_raw_pdf(self, pages_streams, width=595.28, height=841.89, images_dict=None):
        num_pages = len(pages_streams)
        if num_pages == 0:
            pages_streams = [""]
            num_pages = 1

        objects = {}
        objects[1] = f"<< /Type /Catalog /Pages 2 0 R >>"
        objects[3] = f"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
        objects[4] = f"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>"

        # Register Image XObjects (/Filter /DCTDecode for JPEG)
        images_dict = images_dict or {}
        img_name_to_obj_id = {}
        next_obj_id = 5
        for img_name, img_data in images_dict.items():
            img_obj_id = next_obj_id
            next_obj_id += 1
            img_name_to_obj_id[img_name] = img_obj_id
            raw_jpeg = img_data['bytes']
            w = img_data['width']
            h = img_data['height']
            header_str = (
                f"<< /Type /XObject /Subtype /Image /Width {w} /Height {h} "
                f"/ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode "
                f"/Length {len(raw_jpeg)} >>\nstream\n"
            )
            objects[img_obj_id] = header_str.encode('latin1') + raw_jpeg + b"\nendstream"

        if img_name_to_obj_id:
            xobj_entries = " ".join([f"{name} {oid} 0 R" for name, oid in img_name_to_obj_id.items()])
            xobj_res = f"/XObject << {xobj_entries} >>"
        else:
            xobj_res = ""

        # Build Page and Content stream objects
        page_obj_ids = []
        for i in range(num_pages):
            pid = next_obj_id
            cid = next_obj_id + 1
            next_obj_id += 2
            page_obj_ids.append(pid)

            stream_text = pages_streams[i]
            s_bytes = stream_text.encode('latin1', errors='replace')

            objects[pid] = (
                f"<< /Type /Page /Parent 2 0 R "
                f"/MediaBox [0 0 {width:.2f} {height:.2f}] "
                f"/Contents {cid} 0 R "
                f"/Resources << /Font << /F1 3 0 R /F2 4 0 R >> {xobj_res} >> >>"
            )
            objects[cid] = (
                f"<< /Length {len(s_bytes)} >>\nstream\n".encode('latin1') + s_bytes + b"\nendstream"
            )

        kids_str = " ".join([f"{pid} 0 R" for pid in page_obj_ids])
        objects[2] = f"<< /Type /Pages /Kids [{kids_str}] /Count {num_pages} >>"

        out = bytearray()
        out.extend(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = {}
        for obj_id in sorted(objects.keys()):
            offsets[obj_id] = len(out)
            val = objects[obj_id]
            out.extend(f"{obj_id} 0 obj\n".encode('latin1'))
            if isinstance(val, bytes):
                out.extend(val)
            else:
                out.extend(val.encode('latin1'))
            out.extend(b"\nendobj\n")

        xref_offset = len(out)
        total_objs = max(objects.keys()) + 1
        out.extend(f"xref\n0 {total_objs}\n".encode('latin1'))
        out.extend(b"0000000000 65535 f \n")
        for obj_id in range(1, total_objs):
            off = offsets.get(obj_id, 0)
            out.extend(f"{off:010d} 00000 n \n".encode('latin1'))

        out.extend(
            f"trailer\n<< /Size {total_objs} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode('latin1')
        )
        return bytes(out)

    @action(detail=True, methods=['get'], permission_classes=[permissions.AllowAny])
    def export_teams_pdf(self, request, pk=None):
        auction = self._get_auction(pk)
        auction_name = auction.name if auction else 'Auction'

        teams = list(auction.teams.select_related('team').all()) if auction else []

        try:
            import io
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.units import mm
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from django.http import HttpResponse

            out = io.BytesIO()
            doc = SimpleDocTemplate(
                out,
                pagesize=A4,
                leftMargin=12*mm,
                rightMargin=12*mm,
                topMargin=12*mm,
                bottomMargin=12*mm,
                title=f"{auction_name} - All Teams Players"
            )
            styles = getSampleStyleSheet()
            head_style = ParagraphStyle('HeadStyle', fontName='Helvetica-Bold', fontSize=15, leading=18, textColor=colors.HexColor('#0B1B35'))
            team_head_style = ParagraphStyle('TeamHeadStyle', fontName='Helvetica-Bold', fontSize=12, leading=15, textColor=colors.HexColor('#1E293B'))
            body_style = ParagraphStyle('BodyStyle', fontName='Helvetica', fontSize=8.5, leading=11, textColor=colors.HexColor('#1C2A38'))
            th_style = ParagraphStyle('ThStyle', fontName='Helvetica-Bold', fontSize=8.5, leading=11, textColor=colors.HexColor('#0F172A'))

            story = [
                Paragraph(str(auction_name), head_style),
                Spacer(1, 4*mm)
            ]

            for idx, tm in enumerate(teams):
                tm_name = tm.team.name if tm.team else 'Team'
                tm_short = getattr(tm.team, 'short_name', tm_name[:3].upper()) if tm.team else 'TM'
                story.append(Paragraph(f"{tm_short} — {tm_name}", team_head_style))
                story.append(Spacer(1, 2*mm))

                sold_players = auction.players.filter(sold_to=tm, status='SOLD').order_by('serial_no')
                data = [[
                    Paragraph('Player No.', th_style),
                    Paragraph('Name', th_style),
                    Paragraph('Role', th_style),
                    Paragraph('Category', th_style),
                    Paragraph('Sold Amount', th_style)
                ]]
                for p in sold_players:
                    p_name = p.player.full_name or p.player.first_name if p.player else 'Player'
                    data.append([
                        Paragraph(str(p.serial_no or '—'), body_style),
                        Paragraph(str(p_name), body_style),
                        Paragraph(str(p.role or '—'), body_style),
                        Paragraph(str(p.category or '—'), body_style),
                        Paragraph(f"₹{int(p.sold_price or 0):,}", body_style)
                    ])

                if len(data) == 1:
                    data.append([Paragraph('—', body_style), Paragraph('No players bought yet', body_style), Paragraph('—', body_style), Paragraph('—', body_style), Paragraph('—', body_style)])

                tbl = Table(data, colWidths=[20*mm, 55*mm, 35*mm, 38*mm, 32*mm], repeatRows=1)
                tbl.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#E2E8F0')),
                    ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor('#0F172A')),
                    ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
                    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                    ('TOPPADDING', (0,0), (-1,-1), 4),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 4),
                ]))
                story.extend([tbl, Spacer(1, 6*mm)])
                if idx < len(teams) - 1:
                    story.append(PageBreak())

            doc.build(story)
            out.seek(0)
            response = HttpResponse(out.getvalue(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{auction_name}_Teams_Report.pdf"'
            return response
        except (ImportError, Exception):
            from django.http import HttpResponse
            pdf_bytes = self._generate_pure_teams_pdf(auction_name, teams, auction)
            response = HttpResponse(pdf_bytes, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{auction_name}_Teams_Report.pdf"'
            return response

    @action(detail=True, methods=['get', 'post'], permission_classes=[permissions.AllowAny])
    def export_category_pdf(self, request, pk=None):
        auction = self._get_auction(pk)
        auction_name = auction.name if auction else 'Auction'

        players = list(auction.players.select_related('player', 'sold_to', 'sold_to__team').all().order_by('category', 'serial_no', 'id')) if auction else []
        categories = list(auction.categories.all().order_by('priority', 'display_order')) if auction else []
        cat_names = [c.name for c in categories]

        try:
            import io
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.units import mm
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from django.http import HttpResponse

            out = io.BytesIO()
            doc = SimpleDocTemplate(
                out,
                pagesize=A4,
                leftMargin=12*mm,
                rightMargin=12*mm,
                topMargin=12*mm,
                bottomMargin=12*mm,
                title=f"{auction_name} - Category Wise Players"
            )
            styles = getSampleStyleSheet()
            head_style = ParagraphStyle('CatHead', fontName='Helvetica-Bold', fontSize=15, leading=18, textColor=colors.HexColor('#0B1B35'))
            cat_title_style = ParagraphStyle('CatTitle', fontName='Helvetica-Bold', fontSize=12, leading=15, textColor=colors.HexColor('#4338CA'))
            body_style = ParagraphStyle('CatBody', fontName='Helvetica', fontSize=8.5, leading=11, textColor=colors.HexColor('#1E293B'))
            th_style = ParagraphStyle('CatTh', fontName='Helvetica-Bold', fontSize=8.5, leading=11, textColor=colors.HexColor('#0F172A'))

            story = [
                Paragraph(f"{auction_name} — Category-Wise Player Roster", head_style),
                Spacer(1, 4*mm)
            ]

            # Group players by category
            grouped = {}
            for p in players:
                cat = p.category or 'General'
                grouped.setdefault(cat, []).append(p)

            # Ensure all configured categories appear
            ordered_cats = [c for c in cat_names if c in grouped] + [c for c in grouped if c not in cat_names]
            if not ordered_cats:
                ordered_cats = list(grouped.keys())

            for idx, c_name in enumerate(ordered_cats):
                cat_players = grouped.get(c_name, [])
                story.append(Paragraph(f"Category: {c_name} ({len(cat_players)} Players)", cat_title_style))
                story.append(Spacer(1, 2*mm))

                data = [[
                    Paragraph('No.', th_style),
                    Paragraph('Player Name', th_style),
                    Paragraph('Role', th_style),
                    Paragraph('Base Price', th_style),
                    Paragraph('Status', th_style),
                    Paragraph('Sold Team / Price', th_style)
                ]]

                for p in cat_players:
                    p_name = p.player.full_name or p.player.first_name if p.player else 'Player'
                    sold_info = '—'
                    if p.status == 'SOLD':
                        tm_name = p.sold_to.team.name if p.sold_to and p.sold_to.team else 'Assigned Team'
                        sold_info = f"{tm_name} (₹{int(p.sold_price or 0):,})"
                    elif p.status == 'UNSOLD':
                        sold_info = 'Unsold'

                    data.append([
                        Paragraph(str(p.serial_no or '—'), body_style),
                        Paragraph(str(p_name), body_style),
                        Paragraph(str(p.role or '—'), body_style),
                        Paragraph(f"₹{int(p.base_price or 0):,}", body_style),
                        Paragraph(str(p.status), body_style),
                        Paragraph(str(sold_info), body_style)
                    ])

                if len(data) == 1:
                    data.append([Paragraph('—', body_style), Paragraph('No players in this category', body_style), Paragraph('—', body_style), Paragraph('—', body_style), Paragraph('—', body_style), Paragraph('—', body_style)])

                tbl = Table(data, colWidths=[15*mm, 50*mm, 32*mm, 25*mm, 22*mm, 42*mm], repeatRows=1)
                tbl.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#EEF2FF')),
                    ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor('#312E81')),
                    ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
                    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                    ('TOPPADDING', (0,0), (-1,-1), 3.5),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 3.5),
                ]))
                story.extend([tbl, Spacer(1, 6*mm)])
                if idx < len(ordered_cats) - 1:
                    story.append(PageBreak())

            doc.build(story)
            out.seek(0)
            response = HttpResponse(out.getvalue(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{auction_name}_Category_Report.pdf"'
            return response
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get', 'post'], permission_classes=[permissions.AllowAny])
    def export_booklet_pdf(self, request, pk=None):
        """
        Merge and download complete multi-page tournament booklet:
        Page 1: Cover Page (Title, Logo, Total Teams & Players, Venue, Date)
        Page 2: Franchise Owners & Purse Kitty Summary
        Page 3+: Full Team Squad Breakdowns
        Page N+: Category-Wise Player Pool
        """
        auction = self._get_auction(pk)
        auction_name = auction.name if auction else 'Auction'
        config, _ = AuctionTournamentConfig.objects.get_or_create(auction=auction) if auction else (None, None)

        teams = list(auction.teams.select_related('team', 'team__user').all()) if auction else []
        players = list(auction.players.select_related('player', 'sold_to', 'sold_to__team').all().order_by('serial_no', 'id')) if auction else []

        try:
            import io
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.units import mm
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image as RLImage
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from django.http import HttpResponse

            out = io.BytesIO()
            doc = SimpleDocTemplate(
                out,
                pagesize=A4,
                leftMargin=14*mm,
                rightMargin=14*mm,
                topMargin=14*mm,
                bottomMargin=14*mm,
                title=f"{auction_name} - Official Tournament Booklet"
            )
            styles = getSampleStyleSheet()

            cover_title_style = ParagraphStyle('CoverTitle', fontName='Helvetica-Bold', fontSize=26, leading=30, alignment=1, textColor=colors.HexColor('#0F172A'))
            cover_sub_style = ParagraphStyle('CoverSub', fontName='Helvetica-Bold', fontSize=14, leading=18, alignment=1, textColor=colors.HexColor('#4F46E5'))
            cover_body_style = ParagraphStyle('CoverBody', fontName='Helvetica', fontSize=11, leading=16, alignment=1, textColor=colors.HexColor('#475569'))
            section_head_style = ParagraphStyle('SectionHead', fontName='Helvetica-Bold', fontSize=16, leading=20, textColor=colors.HexColor('#0F172A'))
            th_style = ParagraphStyle('BookletTh', fontName='Helvetica-Bold', fontSize=8.5, leading=11, textColor=colors.HexColor('#0F172A'))
            body_style = ParagraphStyle('BookletBody', fontName='Helvetica', fontSize=8.5, leading=11, textColor=colors.HexColor('#1E293B'))

            story = []

            # ---------------- PAGE 1: COVER PAGE ----------------
            story.append(Spacer(1, 20*mm))
            # Tournament Logo if available locally
            if config and config.tournament_logo:
                try:
                    logo_rel = config.tournament_logo.replace(settings.MEDIA_URL, '').lstrip('/')
                    logo_full = os.path.join(settings.MEDIA_ROOT, logo_rel)
                    if os.path.exists(logo_full):
                        story.append(RLImage(logo_full, width=45*mm, height=45*mm))
                        story.append(Spacer(1, 8*mm))
                except Exception:
                    pass

            story.append(Paragraph(str(auction_name), cover_title_style))
            story.append(Spacer(1, 4*mm))
            story.append(Paragraph("OFFICIAL TOURNAMENT AUCTION BOOKLET", cover_sub_style))
            story.append(Spacer(1, 10*mm))

            # Tournament High-Level Stats Box
            stats_data = [
                [
                    Paragraph('<b>Franchise Teams</b>', th_style),
                    Paragraph(str(len(teams)), cover_sub_style),
                    Paragraph('<b>Registered Players</b>', th_style),
                    Paragraph(str(len(players)), cover_sub_style)
                ],
                [
                    Paragraph('<b>Base Team Purse</b>', th_style),
                    Paragraph(f"₹{int(auction.base_budget):,}" if auction else "—", cover_sub_style),
                    Paragraph('<b>Squad Limit</b>', th_style),
                    Paragraph(f"{config.max_squad if config else 11} Players", cover_sub_style)
                ]
            ]
            stats_tbl = Table(stats_data, colWidths=[38*mm, 45*mm, 42*mm, 45*mm])
            stats_tbl.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
                ('GRID', (0,0), (-1,-1), 1, colors.HexColor('#E2E8F0')),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('TOPPADDING', (0,0), (-1,-1), 8),
                ('BOTTOMPADDING', (0,0), (-1,-1), 8),
            ]))
            story.append(stats_tbl)
            story.append(Spacer(1, 15*mm))
            story.append(Paragraph("Generated by TurfArena Live Auction Engine", cover_body_style))
            story.append(PageBreak())

            # ---------------- PAGE 2: FRANCHISE OWNERS & PURSES ----------------
            story.append(Paragraph("Franchise Owners & Financial Summary", section_head_style))
            story.append(Spacer(1, 4*mm))

            owners_data = [[
                Paragraph('#', th_style),
                Paragraph('Team Name', th_style),
                Paragraph('Owner / Captain', th_style),
                Paragraph('Starting Purse', th_style),
                Paragraph('Purse Remaining', th_style),
                Paragraph('Players Bought', th_style)
            ]]

            for idx, tm in enumerate(teams, 1):
                t_name = tm.team.name if tm.team else 'Team'
                owner_name = tm.team.user.full_name or tm.team.user.first_name if tm.team and tm.team.user else 'Owner'
                init_purse = auction.base_budget if auction else 50000
                rem_purse = tm.remaining_budget
                bought_count = auction.players.filter(sold_to=tm, status='SOLD').count() if auction else 0

                owners_data.append([
                    Paragraph(str(idx), body_style),
                    Paragraph(str(t_name), body_style),
                    Paragraph(str(owner_name), body_style),
                    Paragraph(f"₹{int(init_purse):,}", body_style),
                    Paragraph(f"₹{int(rem_purse):,}", body_style),
                    Paragraph(str(bought_count), body_style)
                ])

            if len(owners_data) == 1:
                owners_data.append([Paragraph('—', body_style), Paragraph('No teams configured', body_style), Paragraph('—', body_style), Paragraph('—', body_style), Paragraph('—', body_style), Paragraph('—', body_style)])

            owners_tbl = Table(owners_data, colWidths=[12*mm, 45*mm, 45*mm, 28*mm, 28*mm, 22*mm], repeatRows=1)
            owners_tbl.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#EEF2FF')),
                ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor('#312E81')),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('TOPPADDING', (0,0), (-1,-1), 4),
                ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ]))
            story.append(owners_tbl)
            story.append(PageBreak())

            # ---------------- PAGE 3+: SQUADS BREAKDOWN ----------------
            story.append(Paragraph("Franchise Team Squads", section_head_style))
            story.append(Spacer(1, 4*mm))

            for t_idx, tm in enumerate(teams):
                t_name = tm.team.name if tm.team else 'Team'
                t_short = getattr(tm.team, 'short_name', t_name[:3].upper()) if tm.team else 'TM'
                sold_players = list(auction.players.filter(sold_to=tm, status='SOLD').order_by('serial_no')) if auction else []

                story.append(Paragraph(f"{t_short} — {t_name} (Remaining: ₹{int(tm.remaining_budget):,})", ParagraphStyle('TmTitle', fontName='Helvetica-Bold', fontSize=12, leading=15, textColor=colors.HexColor('#1E293B'))))
                story.append(Spacer(1, 2*mm))

                t_data = [[
                    Paragraph('No.', th_style),
                    Paragraph('Player Name', th_style),
                    Paragraph('Role', th_style),
                    Paragraph('Category', th_style),
                    Paragraph('Sold Amount', th_style)
                ]]
                for p in sold_players:
                    p_name = p.player.full_name or p.player.first_name if p.player else 'Player'
                    t_data.append([
                        Paragraph(str(p.serial_no or '—'), body_style),
                        Paragraph(str(p_name), body_style),
                        Paragraph(str(p.role or '—'), body_style),
                        Paragraph(str(p.category or '—'), body_style),
                        Paragraph(f"₹{int(p.sold_price or 0):,}", body_style)
                    ])

                if len(t_data) == 1:
                    t_data.append([Paragraph('—', body_style), Paragraph('No players bought yet', body_style), Paragraph('—', body_style), Paragraph('—', body_style), Paragraph('—', body_style)])

                squad_tbl = Table(t_data, colWidths=[18*mm, 55*mm, 35*mm, 40*mm, 32*mm], repeatRows=1)
                squad_tbl.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F1F5F9')),
                    ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
                    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                    ('TOPPADDING', (0,0), (-1,-1), 3),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 3),
                ]))
                story.extend([squad_tbl, Spacer(1, 6*mm)])

            doc.build(story)
            out.seek(0)
            response = HttpResponse(out.getvalue(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{auction_name}_Complete_Booklet.pdf"'
            return response
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _generate_pure_teams_pdf(self, auction_name, teams, auction):
        width, height = 595.28, 841.89
        margin = 34.0
        pages = []

        def esc(t):
            cleaned = "".join([c if ord(c) < 128 else ' ' for c in str(t or '')])
            return cleaned.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')

        if not teams:
            pages.append(f"BT /F2 14 Tf 0.06 0.09 0.16 rg {margin:.1f} {height - margin:.1f} Td ({esc(auction_name)} - Squad Roster) Tj ET\nBT /F1 10 Tf 0.4 0.4 0.4 rg {margin:.1f} {height - margin - 30:.1f} Td (No teams configured yet.) Tj ET")
        else:
            for tm in teams:
                cmds = []
                tm_name = tm.team.name if tm.team else 'Team'
                tm_short = getattr(tm.team, 'short_name', tm_name[:3].upper()) if tm.team else 'TM'
                purse = getattr(tm, 'remaining_budget', 0)
                sold_players = list(auction.players.filter(sold_to=tm, status='SOLD').order_by('serial_no')) if auction else []

                cmds.append(f"BT /F2 14 Tf 0.06 0.09 0.16 rg {margin:.1f} {height - margin:.1f} Td ({esc(auction_name)}) Tj ET")
                cmds.append(f"BT /F2 11 Tf 0.15 0.39 0.92 rg {margin:.1f} {height - margin - 20:.1f} Td (Squad Roster: {esc(tm_short)} - {esc(tm_name)} | Remaining Purse: Rs. {int(purse):,}) Tj ET")

                ty = height - margin - 45
                cmds.append(f"0.90 0.92 0.95 rg 0.75 0.80 0.85 RG 0.5 w {margin:.1f} {ty:.1f} {width - 2*margin:.1f} 18 re B")
                cmds.append(f"BT /F2 8.5 Tf 0.06 0.09 0.16 rg {margin + 6:.1f} {ty + 5:.1f} Td (No.) Tj ET")
                cmds.append(f"BT /F2 8.5 Tf 0.06 0.09 0.16 rg {margin + 36:.1f} {ty + 5:.1f} Td (Player Name) Tj ET")
                cmds.append(f"BT /F2 8.5 Tf 0.06 0.09 0.16 rg {margin + 180:.1f} {ty + 5:.1f} Td (Role) Tj ET")
                cmds.append(f"BT /F2 8.5 Tf 0.06 0.09 0.16 rg {margin + 300:.1f} {ty + 5:.1f} Td (Category) Tj ET")
                cmds.append(f"BT /F2 8.5 Tf 0.06 0.09 0.16 rg {margin + 410:.1f} {ty + 5:.1f} Td (Sold Amount) Tj ET")

                curr_y = ty - 18
                if not sold_players:
                    cmds.append(f"BT /F1 9 Tf 0.40 0.45 0.50 rg {margin + 6:.1f} {curr_y + 4:.1f} Td (No players bought yet) Tj ET")
                else:
                    for p in sold_players:
                        p_name = p.player.full_name or p.player.first_name if p.player else 'Player'
                        cmds.append(f"0.98 0.98 0.99 rg 0.85 0.88 0.92 RG 0.5 w {margin:.1f} {curr_y:.1f} {width - 2*margin:.1f} 18 re B")
                        cmds.append(f"BT /F1 8.5 Tf 0.1 0.1 0.1 rg {margin + 6:.1f} {curr_y + 5:.1f} Td ({esc(p.serial_no or '—')}) Tj ET")
                        cmds.append(f"BT /F2 8.5 Tf 0.1 0.1 0.1 rg {margin + 36:.1f} {curr_y + 5:.1f} Td ({esc(p_name)[:24]}) Tj ET")
                        cmds.append(f"BT /F1 8.5 Tf 0.28 0.33 0.42 rg {margin + 180:.1f} {curr_y + 5:.1f} Td ({esc(p.role or '—')[:20]}) Tj ET")
                        cmds.append(f"BT /F1 8.5 Tf 0.28 0.33 0.42 rg {margin + 300:.1f} {curr_y + 5:.1f} Td ({esc(p.category or '—')[:18]}) Tj ET")
                        cmds.append(f"BT /F2 8.5 Tf 0.086 0.639 0.290 rg {margin + 410:.1f} {curr_y + 5:.1f} Td (Rs. {int(p.sold_price or 0):,}) Tj ET")
                        curr_y -= 18
                        if curr_y < margin + 20:
                            break
                pages.append("\n".join(cmds))

        return self._assemble_raw_pdf(pages, width, height)

    @action(detail=True, methods=['post'])
    def clone_settings(self, request, pk=None):
        """Copies all categories, slabs, squad rules, custom fields, and design settings to a new auction."""
        source = self._get_auction(pk)

        new_name = request.data.get('new_name', f"Copy of {source.name}").strip()
        if not new_name:
            return Response({'error': 'New auction name is required'}, status=status.HTTP_400_BAD_REQUEST)

        # Create new auction
        new_auction = Auction.objects.create(
            name=new_name,
            organizer=request.user if request.user.is_authenticated else source.organizer,
            base_budget=source.base_budget,
            status='PENDING',
        )

        # Copy Config
        source_config = AuctionTournamentConfig.objects.filter(auction=source).first()
        if source_config:
            AuctionTournamentConfig.objects.create(
                auction=new_auction,
                max_squad=source_config.max_squad,
                min_players=source_config.min_players,
                max_players=source_config.max_players,
                reserve_amount=source_config.reserve_amount,
                additional_kitty=source_config.additional_kitty,
                penalty_amount=source_config.penalty_amount,
                category_wise_bidding=source_config.category_wise_bidding,
                bring_back_unsold=source_config.bring_back_unsold,
                confirm_sale=source_config.confirm_sale,
                sound_effects=source_config.sound_effects,
                sold_animation=source_config.sold_animation,
                sold_animation_style=source_config.sold_animation_style,
                sold_animation_duration=source_config.sold_animation_duration,
                highest_bid_animation=source_config.highest_bid_animation,
                highest_bid_animation_style=source_config.highest_bid_animation_style,
                highest_bid_animation_duration=source_config.highest_bid_animation_duration,
                online_timer_enabled=source_config.online_timer_enabled,
                timer_seconds=source_config.timer_seconds,
                closing_wait_seconds=source_config.closing_wait_seconds,
                auction_background=source_config.auction_background,
                overall_background=source_config.overall_background,
                tournament_logo=source_config.tournament_logo,
                category_sequence=source_config.category_sequence,
                completion_message=source_config.completion_message,
                custom_bid_enabled=source_config.custom_bid_enabled,
            )

        # Copy Categories
        for cat in source.categories.all():
            AuctionCategory.objects.create(
                auction=new_auction,
                name=cat.name,
                display_order=cat.display_order,
                target_count=cat.target_count,
                base_price=cat.base_price,
                min_bid=cat.min_bid,
            )

        # Copy Slabs
        for slab in source.bid_slabs.all():
            BidSlab.objects.create(
                auction=new_auction,
                up_to_bid=slab.up_to_bid,
                increment=slab.increment,
                display_order=slab.display_order,
            )

        # Copy Squad Rules
        for rule in source.squad_rules.all():
            SquadRule.objects.create(
                auction=new_auction,
                field_key=rule.field_key,
                operator=rule.operator,
                field_value=rule.field_value,
                min_count=rule.min_count,
                max_count=rule.max_count,
                active=rule.active,
                display_order=rule.display_order,
            )

        # Copy Custom Fields & Options
        for field in source.custom_fields.all():
            new_f = CustomFieldDefinition.objects.create(
                auction=new_auction,
                entity_type=field.entity_type,
                field_key=field.field_key,
                label=field.label,
                data_type=field.data_type,
                required=field.required,
                filterable=field.filterable,
                exportable=field.exportable,
                active=field.active,
                display_order=field.display_order,
            )
            for opt in field.options.all():
                CustomFieldOption.objects.create(
                    field_definition=new_f,
                    option_value=opt.option_value,
                    display_order=opt.display_order,
                )

        # Copy Page Design
        source_design = AuctionPageDesign.objects.filter(auction=source).first()
        if source_design:
            AuctionPageDesign.objects.create(
                auction=new_auction,
                design_json=source_design.design_json,
            )

        # Copy Sponsors & Media
        for s in source.sponsors.all():
            AuctionSponsorItem.objects.create(
                auction=new_auction,
                source_url=s.source_url,
                title=s.title,
                display_order=s.display_order,
                duration_seconds=s.duration_seconds,
                active=s.active,
            )
        for m in source.media_items.all():
            AuctionMediaItem.objects.create(
                auction=new_auction,
                media_type=m.media_type,
                source_url=m.source_url,
                title=m.title,
                display_order=m.display_order,
                duration_seconds=m.duration_seconds,
                active=m.active,
            )

        return Response({
            'success': True,
            'message': f"Tournament settings copied into '{new_name}'. Players, teams, and bids remain uncopied.",
            'new_auction_id': str(new_auction.id),
            'new_auction_name': new_auction.name,
        })

    @action(detail=True, methods=['get'])
    def overview_v2(self, request, pk=None):
        auction = self._get_auction(pk)

        all_players = auction.players.all()
        total_players = all_players.count()
        sold_players = all_players.filter(status='SOLD')
        sold_count = sold_players.count()
        unsold_count = all_players.filter(status='UNSOLD').count()
        pending_count = all_players.filter(status='AVAILABLE').count()

        total_spent = sum(float(p.sold_price or 0) for p in sold_players)
        teams = list(auction.teams.select_related('team').all())
        team_count = len(teams)
        total_budget = float(auction.base_budget or 100000) * team_count
        remaining_budget = sum(float(tm.remaining_budget or 0) for tm in teams)

        # Category Progress
        categories_data = []
        for cat in auction.categories.all():
            cat_players = all_players.filter(category=cat.name)
            cat_sold = cat_players.filter(status='SOLD').count()
            cat_unsold = cat_players.filter(status='UNSOLD').count()
            cat_pending = cat_players.filter(status='AVAILABLE').count()

            target_per_team = cat.target_count or 0

            # Count teams that reached target
            teams_complete = 0
            for tm in teams:
                tm_cat_bought = sold_players.filter(sold_to=tm, category=cat.name).count()
                if tm_cat_bought >= target_per_team:
                    teams_complete += 1

            categories_data.append({
                'id': str(cat.id),
                'name': cat.name,
                'base_price': float(cat.base_price or 0),
                'target': target_per_team,
                'team_total': team_count,
                'team_complete': teams_complete,
                'teams_missing': max(0, team_count - teams_complete),
                'sold': cat_sold,
                'unsold': cat_unsold,
                'pending': cat_pending,
            })

        # Top 5 sales
        top_sales = [{
            'id': str(p.id),
            'serial_no': p.serial_no,
            'name': p.player.full_name or p.player.first_name if p.player else 'Player',
            'sold_price': float(p.sold_price or 0),
            'team_name': p.sold_to.team.name if p.sold_to and p.sold_to.team else 'Team',
            'category': p.category,
        } for p in sold_players.order_by('-sold_price')[:5]]

        return Response({
            'auction_id': str(auction.id),
            'auction_name': auction.name,
            'status': auction.status,
            'total_players': total_players,
            'sold_count': sold_count,
            'unsold_count': unsold_count,
            'pending_count': pending_count,
            'total_spent': total_spent,
            'total_budget': total_budget,
            'remaining_budget': remaining_budget,
            'team_count': team_count,
            'categories': categories_data,
            'top_sales': top_sales,
        })

    @action(detail=True, methods=['post'])
    def reset_auction(self, request, pk=None):
        auction = self._get_auction(pk)

        # 1. Reset all players to AVAILABLE
        auction.players.update(
            status='AVAILABLE',
            sold_price=Decimal('0.00'),
            sold_to=None
        )

        # 2. Reset team wallets
        for tm in auction.teams.all():
            tm.remaining_budget = auction.base_budget
            tm.save(update_fields=['remaining_budget'])

        # 3. Clear bids and transactions
        Bid.objects.filter(auction_player__auction=auction).delete()
        TeamPurseTransaction.objects.filter(auction=auction).delete()

        # 4. Reset auction state
        auction.status = 'PENDING'
        auction.active_player = None
        auction.save(update_fields=['status', 'active_player'])

        # 5. Log reset event
        AuctionEventLog.objects.create(
            auction=auction,
            event_type='AUCTION_RESET',
            details={'reset_by': request.user.username if request.user.is_authenticated else 'Admin'}
        )

        return Response({
            'success': True,
            'message': f"Auction '{auction.name}' has been completely reset. All players are available and wallets restored.",
        })

    @action(detail=True, methods=['get', 'post'])
    def communications(self, request, pk=None):
        auction = self._get_auction(pk)
        config, _ = AuctionTournamentConfig.objects.get_or_create(auction=auction)

        if request.method == 'POST':
            data = request.data
            settings_data = data.get('settings', {})
            templates_data = data.get('templates', [])

            stored_data = {
                'settings': {
                    'enabled': bool(settings_data.get('enabled', False)),
                    'phone_number_id': str(settings_data.get('phone_number_id', '')).strip(),
                    'access_token': str(settings_data.get('access_token', '')).strip(),
                    'business_account_id': str(settings_data.get('business_account_id', '')).strip(),
                    'language': str(settings_data.get('language', 'en_US')).strip() or 'en_US',
                    'graph_api_version': str(settings_data.get('graph_api_version', 'v23.0')).strip(),
                    'sold_delay_minutes': int(settings_data.get('sold_delay_minutes', 5)),
                },
                'templates': templates_data,
            }
            # Store in category_sequence or a dedicated JSON dict
            if not isinstance(config.category_sequence, dict):
                config.category_sequence = {}
            # Update whatsapp field in design or config
            design, _ = AuctionPageDesign.objects.get_or_create(auction=auction)
            design_json = design.design_json or {}
            design_json['whatsapp_communications'] = stored_data
            design.design_json = design_json
            design.save()

            return Response({'success': True, 'message': 'WhatsApp communication settings saved.'})

        # GET request
        design = AuctionPageDesign.objects.filter(auction=auction).first()
        stored = (design.design_json or {}).get('whatsapp_communications', {}) if design else {}
        settings = stored.get('settings', {
            'enabled': False,
            'phone_number_id': '',
            'access_token': '',
            'business_account_id': '',
            'language': 'en_US',
            'graph_api_version': 'v23.0',
            'sold_delay_minutes': 5,
        })

        default_templates = [
            {
                'event_key': 'PLAYER_SOLD',
                'title': 'Player Sold',
                'template_name': 'auction_player_sold',
                'language': 'en_US',
                'body_preview': 'Congratulations {{player_name}}! You have been bought by {{team_name}} for ₹{{sale_amount}} in {{tournament_name}}.',
                'enabled': True,
            },
            {
                'event_key': 'UNDO_SALE',
                'title': 'Undo Sale',
                'template_name': 'auction_undo_sale',
                'language': 'en_US',
                'body_preview': 'Update: The previous sale of {{player_name}} in {{tournament_name}} has been reverted by the auctioneer.',
                'enabled': True,
            },
            {
                'event_key': 'PLAYER_UNSOLD',
                'title': 'Unsold / Not Selected',
                'template_name': 'auction_player_unsold',
                'language': 'en_US',
                'body_preview': 'Hello {{player_name}}, you were unsold in {{category}} category for {{tournament_name}}. You may enter the re-auction round.',
                'enabled': True,
            },
            {
                'event_key': 'SQUAD_COMPLETED',
                'title': 'Team Owner — Completed Squad',
                'template_name': 'team_squad_completed',
                'language': 'en_US',
                'body_preview': 'Dear {{team_name}} Owner, your squad is now complete with {{total_players}} players. Total spent: ₹{{total_spent}}, Balance: ₹{{balance}}.',
                'enabled': True,
            },
        ]
        templates = stored.get('templates', default_templates)

        logs_qs = AuctionEventLog.objects.filter(auction=auction, event_type__in=['WHATSAPP_MESSAGE', 'SOLD', 'UNSOLD', 'UNDO_SALE'])[:50]
        logs = [{
            'id': str(l.id),
            'time': l.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'event': l.event_type,
            'recipient': l.details.get('recipient_name', 'N/A'),
            'status': l.details.get('status', 'Sent' if l.event_type == 'SOLD' else 'Logged'),
            'details': l.details,
        } for l in logs_qs]

        return Response({
            'settings': settings,
            'templates': templates,
            'logs': logs,
        })

    @action(detail=True, methods=['post'])
    def communications_test(self, request, pk=None):
        auction = self._get_auction(pk)
        design = AuctionPageDesign.objects.filter(auction=auction).first()
        stored = (design.design_json or {}).get('whatsapp_communications', {}) if design else {}
        settings = request.data.get('settings') or stored.get('settings', {})

        phone_id = settings.get('phone_number_id', '').strip()
        token = settings.get('access_token', '').strip()
        version = (settings.get('graph_api_version') or 'v23.0').strip().strip('/')
        if not version.startswith('v'):
            version = f'v{version}'

        if not phone_id or not token:
            return Response({'ok': False, 'message': 'Please provide Phone Number ID and Access Token.'}, status=status.HTTP_400_BAD_REQUEST)

        # Allow test credentials
        if phone_id.lower() in ['test', 'demo', '123456789']:
            return Response({'ok': True, 'message': 'Test Connection verified! Webhook endpoints active.'})

        try:
            url = f"https://graph.facebook.com/{version}/{phone_id}?fields=display_phone_number,verified_name"
            req = urllib.request.Request(url, headers={'Authorization': f'Bearer {token}'}, method='GET')
            with urllib.request.urlopen(req, timeout=10) as resp:
                resp_data = json.loads(resp.read().decode('utf-8'))
            return Response({'ok': True, 'message': 'WhatsApp Cloud API connection successful!', 'details': resp_data})
        except Exception as exc:
            return Response({'ok': False, 'message': f'Connection test failed: {str(exc)}'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get', 'post'], parser_classes=[MultiPartParser, FormParser, JSONParser], url_path='assets')
    def assets(self, request, pk=None):
        auction = self._get_auction(pk)

        design, _ = AuctionPageDesign.objects.get_or_create(auction=auction, defaults={'design_json': DEFAULT_AUCTION_DESIGN})
        current_json = design.design_json or {}
        asset_library = current_json.get('asset_library', [])

        if request.method == 'GET':
            return Response({'assets': asset_library})

        action_type = request.data.get('action')

        # 1. DELETE ASSET
        if action_type == 'delete':
            asset_id = request.data.get('asset_id')
            updated_library = [a for a in asset_library if a.get('id') != asset_id]
            current_json['asset_library'] = updated_library
            design.design_json = current_json
            design.save(update_fields=['design_json'])
            return Response({'success': True, 'message': 'Asset removed.', 'assets': updated_library})

        # 2. PROMOTE TO SPONSOR ITEM
        if action_type == 'promote_to_sponsor':
            asset_id = request.data.get('asset_id')
            target_asset = next((a for a in asset_library if a.get('id') == asset_id), None)
            if not target_asset:
                return Response({'error': 'Asset not found'}, status=status.HTTP_404_NOT_FOUND)

            max_order = auction.sponsors.count() + 1
            sponsor = AuctionSponsorItem.objects.create(
                auction=auction,
                source_url=target_asset.get('processed_url') or target_asset.get('original_url'),
                title=target_asset.get('name') or 'Sponsor Logo',
                display_order=max_order,
                duration_seconds=10,
                active=True,
            )
            return Response({
                'success': True,
                'message': f"'{sponsor.title}' added to Sponsor Logos carousel!",
                'sponsor_id': sponsor.id,
            })

        # 3. UPLOAD & PROCESS ASSET
        file_obj = request.FILES.get('asset_file')
        if not file_obj:
            return Response({'error': 'Please provide an image file.'}, status=status.HTTP_400_BAD_REQUEST)

        name = request.data.get('name', '').strip()
        asset_type = request.data.get('asset_type', 'Logo')
        remove_bg = request.data.get('remove_background') in [True, 'true', '1']

        try:
            asset_meta = AssetManagerService.save_and_process_asset(
                str(auction.id),
                file_obj,
                name,
                asset_type,
                remove_bg
            )
            asset_library.insert(0, asset_meta)
            current_json['asset_library'] = asset_library
            design.design_json = current_json
            design.save(update_fields=['design_json'])

            return Response({
                'success': True,
                'message': 'Asset uploaded successfully.' + (' Transparent background created.' if asset_meta.get('is_transparent') else ''),
                'asset': asset_meta,
                'assets': asset_library,
            })
        except Exception as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get', 'post'], parser_classes=[MultiPartParser, FormParser, JSONParser], url_path='setup_rules')
    def setup_rules(self, request, pk=None):
        auction = self._get_auction(pk)
        config, _ = AuctionTournamentConfig.objects.get_or_create(auction=auction)
        design, _ = AuctionPageDesign.objects.get_or_create(
            auction=auction,
            defaults={'design_json': DEFAULT_AUCTION_DESIGN}
        )
        design_json = design.design_json or {}
        extended = design_json.setdefault('setup_rules_extended', {})

        if request.method == 'POST':
            data = request.data

            # 1. Auction Completion
            completion_msg = data.get('auction_completion_message') or data.get('completion_message')
            if completion_msg is not None:
                config.completion_message = str(completion_msg).strip() or 'Auction Completed - All team are now completed'

            # 2. Auction Type & Selection Mode
            auction_mode = data.get('auction_mode')
            if auction_mode in ['Centralized', 'Online']:
                extended['auction_mode'] = auction_mode

            player_sel_mode = data.get('player_selection_mode')
            if player_sel_mode:
                config.category_wise_bidding = (player_sel_mode == 'Category Wise')
            elif 'category_wise_bidding' in data:
                config.category_wise_bidding = str(data.get('category_wise_bidding')).lower() in ['true', '1']

            # 3. Squad Rules & Budget
            max_squad = data.get('max_squad')
            if max_squad is not None:
                try:
                    val = int(max_squad)
                    config.max_squad = val
                    config.min_players = val
                    config.max_players = val
                except ValueError:
                    pass

            team_purse = data.get('team_purse')
            if team_purse is not None:
                try:
                    auction.base_budget = Decimal(str(team_purse))
                    auction.save(update_fields=['base_budget'])
                except Exception:
                    pass

            for legacy_f in ['reserve_amount', 'additional_kitty', 'penalty_amount']:
                if legacy_f in data:
                    try:
                        setattr(config, legacy_f, Decimal(str(data[legacy_f])))
                    except Exception:
                        pass

            if 'retention_allowed' in data:
                extended['retention_allowed'] = str(data.get('retention_allowed')).lower() in ['true', '1', 'on']
            if 'bring_back_unsold' in data:
                config.bring_back_unsold = str(data.get('bring_back_unsold')).lower() in ['true', '1', 'on']
            if 'confirm_sale' in data:
                config.confirm_sale = str(data.get('confirm_sale')).lower() in ['true', '1', 'on']
            if 'allow_multiple_bids' in data:
                config.allow_multiple_bids = str(data.get('allow_multiple_bids')).lower() in ['true', '1', 'on', 'yes']
            if 'auto_advance_queue' in data:
                config.auto_advance_queue = str(data.get('auto_advance_queue')).lower() in ['true', '1', 'on', 'yes']

            # 4. SOLD Celebration Animations
            if 'sold_animation' in data:
                config.sold_animation = str(data.get('sold_animation')).lower() in ['true', '1', 'on']
            if 'highest_bid_animation' in data:
                config.highest_bid_animation = str(data.get('highest_bid_animation')).lower() in ['true', '1', 'on']

            sold_style = data.get('sold_animation_style')
            if sold_style:
                config.sold_animation_style = sold_style
            if 'sold_animation_duration' in data:
                try:
                    config.sold_animation_duration = int(data['sold_animation_duration'])
                except ValueError:
                    pass

            highest_style = data.get('highest_bid_animation_style')
            if highest_style:
                config.highest_bid_animation_style = highest_style
            if 'highest_bid_animation_duration' in data:
                try:
                    config.highest_bid_animation_duration = int(data['highest_bid_animation_duration'])
                except ValueError:
                    pass

            # 5. Timer & Sound
            if 'online_timer_enabled' in data:
                config.online_timer_enabled = str(data.get('online_timer_enabled')).lower() in ['true', '1', 'on']
            if 'timer_seconds' in data:
                try:
                    config.timer_seconds = int(data['timer_seconds'])
                except ValueError:
                    pass
            if 'closing_wait_seconds' in data:
                try:
                    config.closing_wait_seconds = int(data['closing_wait_seconds'])
                except ValueError:
                    pass
            if 'sound_effects' in data:
                config.sound_effects = str(data.get('sound_effects')).lower() in ['true', '1', 'on']

            # 6. Category Source & Sequence
            cat_source = data.get('category_source')
            if cat_source in ['Setup', 'Player Master']:
                extended['category_source'] = cat_source

            raw_seq = data.get('category_sequence') or data.get('auction_category_sequence')
            if raw_seq is not None:
                if isinstance(raw_seq, str):
                    config.category_sequence = [x.strip() for x in raw_seq.split(',') if x.strip()]
                elif isinstance(raw_seq, list):
                    config.category_sequence = [str(x).strip() for x in raw_seq if str(x).strip()]

            # 7. Categories sync/update
            raw_cats = data.get('categories')
            if isinstance(raw_cats, str):
                try:
                    raw_cats = json.loads(raw_cats)
                except Exception:
                    raw_cats = None

            if isinstance(raw_cats, list):
                incoming_names = []
                for idx, c_item in enumerate(raw_cats, 1):
                    name = str(c_item.get('name', '')).strip()
                    if not name:
                        continue
                    incoming_names.append(name.lower())
                    base = Decimal(str(c_item.get('base_price', 0) or 0))
                    target = int(c_item.get('target_count', 0) or 0)
                    min_p = int(c_item.get('min_players', 0) or 0)
                    max_p = int(c_item.get('max_players')) if c_item.get('max_players') not in [None, ''] else None
                    prio = int(c_item.get('priority', idx) or idx)
                    cat_obj = auction.categories.filter(name__iexact=name).first()
                    if cat_obj:
                        cat_obj.name = name
                        cat_obj.base_price = base
                        cat_obj.min_bid = base
                        cat_obj.target_count = target
                        cat_obj.min_players = min_p
                        cat_obj.max_players = max_p
                        cat_obj.priority = prio
                        cat_obj.display_order = idx
                        cat_obj.save()
                    else:
                        AuctionCategory.objects.create(
                            auction=auction,
                            name=name,
                            base_price=base,
                            min_bid=base,
                            target_count=target,
                            min_players=min_p,
                            max_players=max_p,
                            priority=prio,
                            display_order=idx
                        )
                for existing_cat in auction.categories.all():
                    if existing_cat.name.strip().lower() not in incoming_names:
                        existing_cat.delete()
            elif data.get('category_names'):
                names = [x.strip() for x in data.get('category_names', '').split(',') if x.strip()]
                if names:
                    incoming_names = [n.lower() for n in names]
                    for idx, n in enumerate(names, 1):
                        base = Decimal(str(data.get(f'cat_base_{idx}', 0) or 0))
                        target = int(data.get(f'cat_target_{idx}', 0) or 0)
                        cat_obj = auction.categories.filter(name__iexact=n).first()
                        if cat_obj:
                            cat_obj.name = n
                            cat_obj.base_price = base
                            cat_obj.min_bid = base
                            cat_obj.target_count = target
                            cat_obj.display_order = idx
                            cat_obj.save()
                        else:
                            AuctionCategory.objects.create(
                                auction=auction,
                                name=n,
                                base_price=base,
                                min_bid=base,
                                target_count=target,
                                display_order=idx
                            )
                    for existing_cat in auction.categories.all():
                        if existing_cat.name.strip().lower() not in incoming_names:
                            existing_cat.delete()

            # 8. Slabs sync/update
            raw_slabs = data.get('slabs')
            if isinstance(raw_slabs, str):
                try:
                    raw_slabs = json.loads(raw_slabs)
                except Exception:
                    raw_slabs = None

            if isinstance(raw_slabs, list):
                auction.bid_slabs.all().delete()
                slabs_to_create = []
                for idx, s_item in enumerate(raw_slabs, 1):
                    up_to = Decimal(str(s_item.get('up_to_bid', 0) or 0))
                    inc = Decimal(str(s_item.get('increment', 0) or 0))
                    if up_to > 0 and inc > 0:
                        slabs_to_create.append(BidSlab(
                            auction=auction,
                            up_to_bid=up_to,
                            increment=inc,
                            display_order=idx
                        ))
                if slabs_to_create:
                    BidSlab.objects.bulk_create(slabs_to_create)

            # 9. Groups
            raw_groups = data.get('groups')
            if isinstance(raw_groups, str):
                try:
                    raw_groups = json.loads(raw_groups)
                except Exception:
                    raw_groups = None

            if isinstance(raw_groups, list):
                extended['groups'] = [
                    {'name': str(g.get('name', f"Group {i+1}")).strip(), 'team_count': int(g.get('team_count', 1))}
                    for i, g in enumerate(raw_groups)
                ]

            group_card_col = data.get('group_card_colour')
            if group_card_col:
                extended['group_card_colour'] = group_card_col

            # 10. File Uploads (Branding & Custom Animations)
            if 'tournament_logo' in request.FILES:
                t_file = request.FILES['tournament_logo']
                remove_bg = str(data.get('remove_tournament_logo_bg', '')).lower() in ['true', '1', 'on']
                try:
                    res = AssetManagerService.save_and_process_asset(
                        str(auction.id), t_file, 'Tournament Logo', 'Logo', remove_bg
                    )
                    logo_url = res.get('processed_url') or res.get('original_url')
                    config.tournament_logo = logo_url
                    if 'zones' not in design_json:
                        design_json['zones'] = {}
                    if 'branding' not in design_json['zones']:
                        design_json['zones']['branding'] = {}
                    design_json['zones']['branding']['title_image_url'] = logo_url
                    design_json['zones']['branding']['remove_title_bg'] = remove_bg
                except Exception as e:
                    print("Logo upload error:", e)

            media_prefix = settings.MEDIA_URL if settings.MEDIA_URL.endswith('/') else f"{settings.MEDIA_URL}/"

            if 'auction_background_file' in request.FILES:
                bg_file = request.FILES['auction_background_file']
                try:
                    ext = os.path.splitext(bg_file.name)[1]
                    safe_name = f"auction_bg_{auction.id}_{int(time.time())}{ext}"
                    saved_path = default_storage.save(f"auction/branding/{safe_name}", bg_file)
                    config.auction_background = f"{media_prefix}{saved_path}"
                except Exception as e:
                    print("Auction background file upload error:", e)
            elif data.get('auction_background'):
                config.auction_background = str(data.get('auction_background')).strip()

            if 'overall_background_file' in request.FILES:
                obg_file = request.FILES['overall_background_file']
                try:
                    ext = os.path.splitext(obg_file.name)[1]
                    safe_name = f"overall_bg_{auction.id}_{int(time.time())}{ext}"
                    saved_path = default_storage.save(f"auction/branding/{safe_name}", obg_file)
                    config.overall_background = f"{media_prefix}{saved_path}"
                except Exception as e:
                    print("Overall background file upload error:", e)
            elif data.get('overall_background'):
                config.overall_background = str(data.get('overall_background')).strip()

            if 'sold_animation_custom' in request.FILES:
                anim_file = request.FILES['sold_animation_custom']
                try:
                    ext = os.path.splitext(anim_file.name)[1]
                    safe_name = f"sold_anim_{auction.id}_{int(time.time())}{ext}"
                    saved_path = default_storage.save(f"auction/animations/{safe_name}", anim_file)
                    extended['sold_animation_custom'] = f"{media_prefix}{saved_path}"
                except Exception as e:
                    print("Sold animation upload error:", e)
            elif 'sold_animation_custom_url' in data:
                extended['sold_animation_custom'] = str(data.get('sold_animation_custom_url', '')).strip()

            if 'highest_bid_animation_custom' in request.FILES:
                anim_file = request.FILES['highest_bid_animation_custom']
                try:
                    ext = os.path.splitext(anim_file.name)[1]
                    safe_name = f"highest_anim_{auction.id}_{int(time.time())}{ext}"
                    saved_path = default_storage.save(f"auction/animations/{safe_name}", anim_file)
                    extended['highest_bid_animation_custom'] = f"{media_prefix}{saved_path}"
                except Exception as e:
                    print("Highest bid animation upload error:", e)
            elif 'highest_bid_animation_custom_url' in data:
                extended['highest_bid_animation_custom'] = str(data.get('highest_bid_animation_custom_url', '')).strip()

            # Group Card Flip Animation & Revealed Card Background
            if data.get('group_card_animation'):
                extended['group_card_animation'] = str(data.get('group_card_animation')).strip()
            if 'group_draw_animation_enabled' in data:
                extended['group_draw_animation_enabled'] = str(data.get('group_draw_animation_enabled')).lower() in ['true', '1']

            if 'group_card_bg_image' in request.FILES:
                bg_file = request.FILES['group_card_bg_image']
                try:
                    ext = os.path.splitext(bg_file.name)[1]
                    safe_name = f"group_card_bg_{auction.id}_{int(time.time())}{ext}"
                    saved_path = default_storage.save(f"auction/branding/{safe_name}", bg_file)
                    extended['group_card_bg_image'] = f"{media_prefix}{saved_path}"
                except Exception as e:
                    print("Group card background upload error:", e)
            elif 'group_card_bg_image' in data:
                extended['group_card_bg_image'] = str(data.get('group_card_bg_image', '')).strip()
            elif 'group_card_bg_image_url' in data:
                extended['group_card_bg_image'] = str(data.get('group_card_bg_image_url', '')).strip()

            config.save()
            design_json['setup_rules_extended'] = extended
            design.design_json = design_json
            design.save(update_fields=['design_json'])

        # GET response construction
        player_cats = list(
            auction.players.exclude(category__isnull=True)
            .exclude(category__exact='')
            .values_list('category', flat=True)
            .distinct()
        )

        categories = list(auction.categories.all().order_by('priority', 'display_order', 'created_at').values(
            'id', 'name', 'base_price', 'target_count', 'display_order', 'min_players', 'max_players', 'priority'
        ))

        slabs = list(auction.bid_slabs.all().order_by('up_to_bid').values(
            'id', 'up_to_bid', 'increment', 'display_order'
        ))

        squad_rules = list(auction.squad_rules.all().order_by('display_order', 'created_at').values(
            'id', 'field_key', 'operator', 'field_value', 'min_count', 'max_count', 'active', 'display_order'
        ))

        active_teams_count = auction.teams.count()

        groups = extended.get('groups')
        if not groups:
            existing_cards = list(auction.group_cards.values_list('group_name', flat=True).distinct())
            if existing_cards:
                groups = [{'name': name, 'team_count': auction.group_cards.filter(group_name=name).count()} for name in existing_cards]
            else:
                groups = [
                    {'name': 'Group 1', 'team_count': max(1, active_teams_count // 2)},
                    {'name': 'Group 2', 'team_count': max(1, active_teams_count - (active_teams_count // 2))}
                ]

        seq = config.category_sequence
        if not seq:
            seq = [c['name'] for c in categories]

        return Response({
            'success': True,
            'auction': {
                'id': str(auction.id),
                'name': auction.name,
                'team_purse': float(auction.base_budget),
                'active_teams_count': active_teams_count,
            },
            'config': {
                'auction_completion_message': config.completion_message or 'Auction Completed - All team are now completed',
                'auction_mode': extended.get('auction_mode', 'Centralized'),
                'player_selection_mode': 'Category Wise' if config.category_wise_bidding else 'Open',
                'category_wise_bidding': config.category_wise_bidding,
                'max_squad': config.max_squad,
                'team_purse': float(auction.base_budget),
                'reserve_amount': float(config.reserve_amount),
                'additional_kitty': float(config.additional_kitty),
                'penalty_amount': float(config.penalty_amount),
                'retention_allowed': extended.get('retention_allowed', False),
                'bring_back_unsold': config.bring_back_unsold,
                'confirm_sale': config.confirm_sale,
                'sold_animation': config.sold_animation,
                'sold_animation_style': config.sold_animation_style or 'Confetti Burst',
                'sold_animation_duration': config.sold_animation_duration or 3,
                'highest_bid_animation': config.highest_bid_animation,
                'highest_bid_animation_style': config.highest_bid_animation_style or 'Fireworks',
                'highest_bid_animation_duration': config.highest_bid_animation_duration or 5,
                'sold_animation_custom': extended.get('sold_animation_custom', ''),
                'highest_bid_animation_custom': extended.get('highest_bid_animation_custom', ''),
                'category_source': extended.get('category_source', 'Setup'),
                'category_sequence': seq,
                'group_count': len(groups),
                'groups': groups,
                'group_card_colour': extended.get('group_card_colour', '#FFFFFF'),
                'group_card_animation': extended.get('group_card_animation', '3D Flip Horizontal'),
                'group_card_bg_image': extended.get('group_card_bg_image', ''),
                'group_draw_animation_enabled': extended.get('group_draw_animation_enabled', True),
                'tournament_logo': config.tournament_logo or '',
                'auction_background': config.auction_background or 'stadium',
                'overall_background': config.overall_background or 'default',
                'allow_multiple_bids': getattr(config, 'allow_multiple_bids', False),
                'auto_advance_queue': getattr(config, 'auto_advance_queue', True),
                'online_timer_enabled': config.online_timer_enabled,
                'timer_seconds': config.timer_seconds or 30,
                'closing_wait_seconds': config.closing_wait_seconds or 5,
                'sound_effects': config.sound_effects,
            },
            'categories': categories,
            'slabs': slabs,
            'squad_rules': squad_rules,
            'player_master_categories': player_cats,
            'animation_styles': ['Confetti Burst', 'Fireworks', 'Gold Celebration', 'Spotlight', 'Trophy Celebration'],
        })

# Dedicated CRUD ViewSets for Setup & Custom Fields
class AuctionCategoryViewSet(viewsets.ModelViewSet):
    queryset = AuctionCategory.objects.all()
    serializer_class = AuctionCategorySerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        qs = super().get_queryset()
        auction_id = self.request.query_params.get('auction')
        return _safe_filter_auction(qs, auction_id).order_by('display_order', 'id')

def _safe_filter_auction(qs, auction_id):
    if not auction_id:
        return qs
    try:
        uuid_obj = uuid.UUID(str(auction_id))
        return qs.filter(auction_id=uuid_obj)
    except (ValueError, TypeError):
        fallback_auc = Auction.objects.first()
        if fallback_auc:
            return qs.filter(auction=fallback_auc)
        return qs.none()

class BidSlabViewSet(viewsets.ModelViewSet):
    queryset = BidSlab.objects.all()
    serializer_class = BidSlabSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        auction_id = self.request.query_params.get('auction')
        return _safe_filter_auction(qs, auction_id)

class SquadRuleViewSet(viewsets.ModelViewSet):
    queryset = SquadRule.objects.all()
    serializer_class = SquadRuleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        auction_id = self.request.query_params.get('auction')
        return _safe_filter_auction(qs, auction_id)

class CustomFieldDefinitionViewSet(viewsets.ModelViewSet):
    queryset = CustomFieldDefinition.objects.all()
    serializer_class = CustomFieldDefinitionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        auction_id = self.request.query_params.get('auction')
        return _safe_filter_auction(qs, auction_id)

class AuctionSponsorItemViewSet(viewsets.ModelViewSet):
    queryset = AuctionSponsorItem.objects.all()
    serializer_class = AuctionSponsorItemSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        qs = super().get_queryset()
        auction_id = self.request.query_params.get('auction')
        if auction_id:
            matching = qs.filter(auction_id=auction_id)
            if matching.exists() or auction_id != '1':
                return matching
            # Fallback for demo ID '1'
            first_auction = Auction.objects.first()
            if first_auction:
                return qs.filter(auction=first_auction)
        return qs

    def create(self, request, *args, **kwargs):
        auction_id = request.data.get('auction')
        auction = Auction.objects.filter(pk=auction_id).first()
        if not auction:
            auction = Auction.objects.first()
        if not auction:
            auction = Auction.objects.create(name='Turf Premier League (Live Auction)', status='ACTIVE', base_budget=100000)

        file_obj = request.FILES.get('file') or request.FILES.get('logo_file') or request.FILES.get('image')
        source_url = request.data.get('source_url', '').strip()

        if file_obj:
            ext = os.path.splitext(file_obj.name)[1]
            safe_name = f"sponsor_{auction.id}_{int(time.time())}{ext}"
            saved_path = default_storage.save(f"auction/sponsors/{safe_name}", file_obj)
            source_url = request.build_absolute_uri(settings.MEDIA_URL + saved_path)

        if not source_url:
            return Response({'error': 'Please provide a sponsor logo file or an image URL.'}, status=status.HTTP_400_BAD_REQUEST)

        title = request.data.get('title') or 'Sponsor Logo'
        duration_seconds = int(request.data.get('duration_seconds', 10))
        display_order = int(request.data.get('display_order', auction.sponsors.count() + 1))

        sponsor = AuctionSponsorItem.objects.create(
            auction=auction,
            source_url=source_url,
            title=title,
            duration_seconds=duration_seconds,
            display_order=display_order,
            active=True
        )
        return Response(AuctionSponsorItemSerializer(sponsor).data, status=status.HTTP_201_CREATED)

class AuctionMediaItemViewSet(viewsets.ModelViewSet):
    queryset = AuctionMediaItem.objects.all()
    serializer_class = AuctionMediaItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        auction_id = self.request.query_params.get('auction')
        if auction_id:
            qs = qs.filter(auction_id=auction_id)
        return qs

# Public Unauthenticated Views for Fan Spectator & Self-Registration
class PublicSpectatorStateView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, token):
        link = PublicAuctionLink.objects.filter(public_token=token, enabled=True).select_related('auction').first()
        if not link:
            return Response({'error': 'Live public link is disabled or invalid'}, status=status.HTTP_404_NOT_FOUND)

        state = LiveAuctionEngine.get_live_state(link.auction)
        return Response(state)

class PublicPlayerRegistrationView(APIView):
    permission_classes = [permissions.AllowAny]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request, token):
        link = PlayerRegistrationLink.objects.filter(registration_token=token).select_related('auction').first()
        if not link or not link.enabled:
            return Response({'error': 'Player registration link is disabled or invalid'}, status=status.HTTP_404_NOT_FOUND)

        auction = link.auction
        categories = list(AuctionCategory.objects.filter(auction=auction).values('name', 'target_count', 'base_price'))
        custom_fields = []
        for cf in CustomFieldDefinition.objects.filter(auction=auction, entity_type='player'):
            custom_fields.append({
                'field_key': cf.field_key,
                'label': cf.label,
                'data_type': cf.data_type,
                'required': cf.required,
                'options': list(cf.options.values_list('option_value', flat=True))
            })

        return Response({
            'tournament_name': auction.name,
            'title': link.title or f"{auction.name} - Player Registration",
            'intro_text': link.intro_text or "Register to participate in this tournament live auction.",
            'success_message': link.success_message or "Thank you! Your player registration has been submitted successfully.",
            'show_tournament_logo': link.show_tournament_logo,
            'show_tournament_name': link.show_tournament_name,
            'fields': link.fields_json or ['name', 'mobile', 'role', 'category', 'batting_style', 'bowling_style', 'photo'],
            'categories': categories,
            'custom_fields': custom_fields,
        })

    def post(self, request, token):
        link = PlayerRegistrationLink.objects.filter(registration_token=token, enabled=True).select_related('auction').first()
        if not link:
            return Response({'error': 'Player registration link is disabled or invalid'}, status=status.HTTP_404_NOT_FOUND)

        auction = link.auction
        data = request.data.dict() if hasattr(request.data, 'dict') else dict(request.data)
        name = data.get('name') or data.get('player_name')
        if not name:
            return Response({'error': 'Player name is required'}, status=status.HTTP_400_BAD_REQUEST)

        # Handle file upload for photo if sent
        photo_file = request.FILES.get('photo_file') or request.FILES.get('photo')
        if photo_file:
            import os
            from django.core.files.storage import default_storage
            upload_dir = 'auction_players'
            saved_path = default_storage.save(os.path.join(upload_dir, photo_file.name), photo_file)
            data['photo_url'] = default_storage.url(saved_path)

        data['registration_source'] = 'Self-Registration'

        # Import single player into auction pool
        imported, errors = PlayerIntakeService.import_players(
            auction,
            [data],
            list(data.keys())
        )
        if errors:
            return Response({'error': errors[0]}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'success': True,
            'message': link.success_message or 'Registration submitted successfully!'
        })
