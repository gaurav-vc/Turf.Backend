import secrets
import random
from decimal import Decimal
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

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
    'version': 3,
    'grid': 5,
    'background_mode': 'stadium',
    'zones': {
        'team_grid': {'max_columns': 14, 'rows': 2, 'box_width': 120, 'box_height': 54, 'gap': 6},
        'action_bar': {'width': 455, 'columns': 4, 'button_height': 42, 'gap': 6, 'show_more': True},
        'bid_history': {'width': 300, 'rows': 6, 'newest_first': True},
        'media_window': {'x': 74, 'y': 5, 'w': 24, 'h': 20, 'enabled': True},
        'branding': {'logo_count': 1, 'logo_position': 'center', 'logo_size': 38, 'title_size': 30},
        'sponsor_window': {'x': 72, 'y': 72, 'w': 24, 'h': 18, 'enabled': True, 'mode': 'rotate'},
    },
    'elements': {
        'player_category': {'x': 4, 'y': 3, 'w': 92, 'h': 6, 'font_size': 26, 'colour': '#FFD54A', 'font_family': 'Arial', 'bold': True, 'align': 'center', 'selected': True, 'show_label': False},
        'player_number': {'x': 4, 'y': 11, 'w': 20, 'h': 5, 'font_size': 17, 'colour': '#B8C7DA', 'font_family': 'Arial', 'bold': True, 'align': 'left', 'selected': True, 'show_label': False},
        'player_photo': {'x': 5, 'y': 18, 'w': 28, 'h': 61, 'font_size': 16, 'colour': '#FFFFFF', 'font_family': 'Arial', 'bold': False, 'align': 'center', 'selected': True},
        'player_name': {'x': 36, 'y': 15, 'w': 59, 'h': 10, 'font_size': 44, 'colour': '#FFFFFF', 'font_family': 'Arial', 'bold': True, 'align': 'left', 'selected': True, 'show_label': False},
        'role': {'x': 36, 'y': 27, 'w': 28, 'h': 6, 'font_size': 19, 'colour': '#D8E2EF', 'font_family': 'Arial', 'bold': True, 'align': 'left', 'selected': True, 'show_label': False},
        'batting_style': {'x': 36, 'y': 36, 'w': 25, 'h': 7, 'font_size': 15, 'colour': '#FFFFFF', 'font_family': 'Arial', 'bold': False, 'align': 'left', 'selected': True, 'show_label': True},
        'bowling_style': {'x': 63, 'y': 36, 'w': 25, 'h': 7, 'font_size': 15, 'colour': '#FFFFFF', 'font_family': 'Arial', 'bold': False, 'align': 'left', 'selected': True, 'show_label': True},
        'current_bid': {'x': 36, 'y': 55, 'w': 30, 'h': 14, 'font_size': 48, 'colour': '#FFD54A', 'font_family': 'Arial', 'bold': True, 'align': 'left', 'selected': True, 'show_label': True},
        'bidder_name': {'x': 68, 'y': 55, 'w': 27, 'h': 8, 'font_size': 22, 'colour': '#FFFFFF', 'font_family': 'Arial', 'bold': True, 'align': 'right', 'selected': True, 'show_label': False},
        'balance': {'x': 68, 'y': 66, 'w': 27, 'h': 6, 'font_size': 15, 'colour': '#B9C7D7', 'font_family': 'Arial', 'bold': True, 'align': 'right', 'selected': True, 'show_label': True},
        'max_bid': {'x': 68, 'y': 74, 'w': 27, 'h': 6, 'font_size': 15, 'colour': '#FFFFFF', 'font_family': 'Arial', 'bold': True, 'align': 'right', 'selected': True, 'show_label': True},
        'base_price': {'x': 5, 'y': 81, 'w': 28, 'h': 7, 'font_size': 20, 'colour': '#FFFFFF', 'font_family': 'Arial', 'bold': True, 'align': 'center', 'selected': True, 'show_label': True},
    }
}

class Phase2AuctionConsoleViewSet(viewsets.ViewSet):
    """
    Dedicated ViewSet for Phase 2 V24 Live Auction Console Operations.
    """
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=True, methods=['get'])
    def live_state(self, request, pk=None):
        """Returns full reactive state for live auction broadcast & controls."""
        try:
            auction = Auction.objects.get(pk=pk)
        except Auction.DoesNotExist:
            return Response({'error': 'Auction not found'}, status=status.HTTP_404_NOT_FOUND)

        state = LiveAuctionEngine.get_live_state(auction)
        return Response(state)

    @action(detail=True, methods=['post'])
    def bid(self, request, pk=None):
        """Places a team quick bid or custom bid."""
        try:
            auction = Auction.objects.get(pk=pk)
        except Auction.DoesNotExist:
            return Response({'error': 'Auction not found'}, status=status.HTTP_404_NOT_FOUND)

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
        auction = Auction.objects.filter(pk=pk).first()
        if not auction:
            return Response({'error': 'Auction not found'}, status=status.HTTP_404_NOT_FOUND)

        ok, result = LiveAuctionEngine.sell_active_player(auction)
        if not ok:
            return Response({'error': result}, status=status.HTTP_400_BAD_REQUEST)

        state = LiveAuctionEngine.get_live_state(auction)
        return Response({'success': True, 'celebration': 'sold', 'state': state})

    @action(detail=True, methods=['post'])
    def hammer_unsold(self, request, pk=None):
        """HAMMER: Marks active player UNSOLD."""
        auction = Auction.objects.filter(pk=pk).first()
        if not auction:
            return Response({'error': 'Auction not found'}, status=status.HTTP_404_NOT_FOUND)

        ok, result = LiveAuctionEngine.unsold_active_player(auction)
        if not ok:
            return Response({'error': result}, status=status.HTTP_400_BAD_REQUEST)

        state = LiveAuctionEngine.get_live_state(auction)
        return Response({'success': True, 'state': state})

    @action(detail=True, methods=['post'])
    def undo_sale(self, request, pk=None):
        """Undoes the most recent sale and restores team wallet balance."""
        auction = Auction.objects.filter(pk=pk).first()
        if not auction:
            return Response({'error': 'Auction not found'}, status=status.HTTP_404_NOT_FOUND)

        ok, result = LiveAuctionEngine.undo_sale(auction)
        if not ok:
            return Response({'error': result}, status=status.HTTP_400_BAD_REQUEST)

        state = LiveAuctionEngine.get_live_state(auction)
        return Response({'success': True, 'message': 'Sale undone successfully.', 'state': state})

    @action(detail=True, methods=['post'])
    def undo_bid(self, request, pk=None):
        """Undoes the latest bid placed."""
        auction = Auction.objects.filter(pk=pk).first()
        if not auction:
            return Response({'error': 'Auction not found'}, status=status.HTTP_404_NOT_FOUND)

        ok, result = LiveAuctionEngine.undo_bid(auction)
        if not ok:
            return Response({'error': result}, status=status.HTTP_400_BAD_REQUEST)

        state = LiveAuctionEngine.get_live_state(auction)
        return Response({'success': True, 'state': state})

    @action(detail=True, methods=['post'])
    def reset_bid(self, request, pk=None):
        """Resets all bids for current active player back to 0."""
        auction = Auction.objects.filter(pk=pk).first()
        if not auction:
            return Response({'error': 'Auction not found'}, status=status.HTTP_404_NOT_FOUND)

        ok, result = LiveAuctionEngine.reset_bid(auction)
        if not ok:
            return Response({'error': result}, status=status.HTTP_400_BAD_REQUEST)

        state = LiveAuctionEngine.get_live_state(auction)
        return Response({'success': True, 'state': state})

    @action(detail=True, methods=['post'])
    def select_player_no(self, request, pk=None):
        """Puts a player on block by Player No / Serial No."""
        auction = Auction.objects.filter(pk=pk).first()
        if not auction:
            return Response({'error': 'Auction not found'}, status=status.HTTP_404_NOT_FOUND)

        serial_no = request.data.get('serial_no')
        if not serial_no:
            return Response({'error': 'serial_no is required'}, status=status.HTTP_400_BAD_REQUEST)

        ok, result = LiveAuctionEngine.select_player_by_number(auction, int(serial_no))
        if not ok:
            return Response({'error': result}, status=status.HTTP_400_BAD_REQUEST)

        state = LiveAuctionEngine.get_live_state(auction)
        return Response({'success': True, 'state': state})

    @action(detail=True, methods=['post'])
    def reauction(self, request, pk=None):
        """Starts re-auction round for unsold players."""
        auction = Auction.objects.filter(pk=pk).first()
        if not auction:
            return Response({'error': 'Auction not found'}, status=status.HTTP_404_NOT_FOUND)

        category = request.data.get('category')
        ok, msg = LiveAuctionEngine.start_reauction_round(auction, category)
        if not ok:
            return Response({'error': msg}, status=status.HTTP_400_BAD_REQUEST)

        state = LiveAuctionEngine.get_live_state(auction)
        return Response({'success': True, 'message': msg, 'state': state})

    @action(detail=True, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def bulk_import_players(self, request, pk=None):
        """Imports players from an uploaded CSV or Excel file."""
        auction = Auction.objects.filter(pk=pk).first()
        if not auction:
            return Response({'error': 'Auction not found'}, status=status.HTTP_404_NOT_FOUND)

        file_obj = request.FILES.get('file')
        if not file_obj:
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

    @action(detail=True, methods=['get', 'post'])
    def page_design(self, request, pk=None):
        """Gets or updates broadcast auction page design layout JSON."""
        auction = Auction.objects.filter(pk=pk).first()
        if not auction:
            return Response({'error': 'Auction not found'}, status=status.HTTP_404_NOT_FOUND)

        design_obj, _ = AuctionPageDesign.objects.get_or_create(
            auction=auction,
            defaults={'design_json': DEFAULT_AUCTION_DESIGN}
        )

        if request.method == 'POST':
            design_json = request.data.get('design_json') or request.data
            design_obj.design_json = design_json
            design_obj.save()
            return Response({'success': True, 'design_json': design_obj.design_json})

        return Response(design_obj.design_json)

    @action(detail=True, methods=['get', 'post'])
    def public_link(self, request, pk=None):
        """Gets or regenerates the public spectator viewer token."""
        auction = Auction.objects.filter(pk=pk).first()
        if not auction:
            return Response({'error': 'Auction not found'}, status=status.HTTP_404_NOT_FOUND)

        link_obj = getattr(auction, 'public_link', None)
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
        auction = Auction.objects.filter(pk=pk).first()
        if not auction:
            return Response({'error': 'Auction not found'}, status=status.HTTP_404_NOT_FOUND)

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

    @action(detail=True, methods=['get', 'post'])
    def group_draw(self, request, pk=None):
        """Group draw stage: generates blind cards, assigns, or reveals cards."""
        auction = Auction.objects.filter(pk=pk).first()
        if not auction:
            return Response({'error': 'Auction not found'}, status=status.HTTP_404_NOT_FOUND)

        if request.method == 'POST':
            draw_action = request.data.get('action')
            if draw_action == 'generate':
                group_names = request.data.get('groups', ['Group A', 'Group B'])
                teams_count = auction.teams.count()
                if teams_count == 0:
                    return Response({'error': 'No teams in auction'}, status=status.HTTP_400_BAD_REQUEST)
                
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
                team = auction.teams.filter(id=team_id).first()
                if card and team:
                    card.team = team
                    card.save()

            elif draw_action == 'reveal':
                card_number = request.data.get('card_number')
                card = auction.group_cards.filter(card_number=card_number).first()
                if card:
                    card.revealed = True
                    card.save()

            elif draw_action == 'reset':
                auction.group_cards.all().delete()

        cards = auction.group_cards.all().order_by('card_number')
        return Response(GroupDrawCardSerializer(cards, many=True).data)

    @action(detail=True, methods=['get'])
    def all_teams_report(self, request, pk=None):
        """Generates comprehensive roster & financial summary for all franchise teams."""
        auction = Auction.objects.filter(pk=pk).first()
        if not auction:
            return Response({'error': 'Auction not found'}, status=status.HTTP_404_NOT_FOUND)

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
    def export_teams_pdf(self, request, pk=None):
        auction = Auction.objects.filter(pk=pk).first()
        if not auction:
            return Response({'error': 'Auction not found'}, status=status.HTTP_404_NOT_FOUND)

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
                title=f"{auction.name} - All Teams Players"
            )
            styles = getSampleStyleSheet()
            head_style = ParagraphStyle('HeadStyle', fontName='Helvetica-Bold', fontSize=15, leading=18, textColor=colors.HexColor('#0B1B35'))
            team_head_style = ParagraphStyle('TeamHeadStyle', fontName='Helvetica-Bold', fontSize=12, leading=15, textColor=colors.HexColor('#1E293B'))
            body_style = ParagraphStyle('BodyStyle', fontName='Helvetica', fontSize=8.5, leading=11, textColor=colors.HexColor('#1C2A38'))
            th_style = ParagraphStyle('ThStyle', fontName='Helvetica-Bold', fontSize=8.5, leading=11, textColor=colors.HexColor('#0F172A'))

            story = [
                Paragraph(str(auction.name), head_style),
                Spacer(1, 4*mm)
            ]

            teams = list(auction.teams.select_related('team').all())
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
            response['Content-Disposition'] = f'attachment; filename="{auction.name}_Squad_Report.pdf"'
            return response
        except Exception as exc:
            return Response({'error': f'PDF generation unavailable: {str(exc)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def clone_settings(self, request, pk=None):
        """Copies all categories, slabs, squad rules, custom fields, and design settings to a new auction."""
        source = Auction.objects.filter(pk=pk).first()
        if not source:
            return Response({'error': 'Source auction not found'}, status=status.HTTP_404_NOT_FOUND)

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
    def overview(self, request, pk=None):
        auction = Auction.objects.filter(pk=pk).first()
        if not auction:
            return Response({'error': 'Auction not found'}, status=status.HTTP_404_NOT_FOUND)

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
        auction = Auction.objects.filter(pk=pk).first()
        if not auction:
            return Response({'error': 'Auction not found'}, status=status.HTTP_404_NOT_FOUND)

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
        auction = Auction.objects.filter(pk=pk).first()
        if not auction:
            return Response({'error': 'Auction not found'}, status=status.HTTP_404_NOT_FOUND)

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
        auction = Auction.objects.filter(pk=pk).first()
        if not auction:
            return Response({'error': 'Auction not found'}, status=status.HTTP_404_NOT_FOUND)

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
        auction = Auction.objects.filter(pk=pk).first()
        if not auction:
            return Response({'error': 'Auction not found'}, status=status.HTTP_404_NOT_FOUND)

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

# Dedicated CRUD ViewSets for Setup & Custom Fields
class AuctionCategoryViewSet(viewsets.ModelViewSet):
    queryset = AuctionCategory.objects.all()
    serializer_class = AuctionCategorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        auction_id = self.request.query_params.get('auction')
        if auction_id:
            qs = qs.filter(auction_id=auction_id)
        return qs

class BidSlabViewSet(viewsets.ModelViewSet):
    queryset = BidSlab.objects.all()
    serializer_class = BidSlabSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        auction_id = self.request.query_params.get('auction')
        if auction_id:
            qs = qs.filter(auction_id=auction_id)
        return qs

class SquadRuleViewSet(viewsets.ModelViewSet):
    queryset = SquadRule.objects.all()
    serializer_class = SquadRuleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        auction_id = self.request.query_params.get('auction')
        if auction_id:
            qs = qs.filter(auction_id=auction_id)
        return qs

class CustomFieldDefinitionViewSet(viewsets.ModelViewSet):
    queryset = CustomFieldDefinition.objects.all()
    serializer_class = CustomFieldDefinitionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        auction_id = self.request.query_params.get('auction')
        if auction_id:
            qs = qs.filter(auction_id=auction_id)
        return qs

class AuctionSponsorItemViewSet(viewsets.ModelViewSet):
    queryset = AuctionSponsorItem.objects.all()
    serializer_class = AuctionSponsorItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        auction_id = self.request.query_params.get('auction')
        if auction_id:
            qs = qs.filter(auction_id=auction_id)
        return qs

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
