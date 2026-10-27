"""
Live Auction State Engine & Operations
Ported from Cricket Auction Phase 2 V24 authoritative logic.
"""
from decimal import Decimal
from django.db import transaction
from ..models import Auction, AuctionTeam, AuctionPlayer, Bid
from ..models_v24 import AuctionEventLog, TeamPurseTransaction, AuctionCategory
from .max_bid_calculator import (
    team_financials, 
    bid_increment, 
    valid_custom_bid, 
    allowed_team_for_lot
)

class LiveAuctionEngine:
    @staticmethod
    def get_live_state(auction):
        """
        Returns complete real-time state for live auction console & spectator screens.
        """
        active_player = auction.active_player
        player_data = None
        bids_history = []
        highest_bid = None

        if active_player:
            bids = active_player.bids.select_related('team__team').order_by('-created_at')[:10]
            for b in bids:
                t_name = b.team.team.name if b.team and b.team.team else "Team"
                s_name = getattr(b.team.team, 'short_name', t_name[:3].upper()) if b.team and b.team.team else "TM"
                bids_history.append({
                    'id': str(b.id),
                    'amount': float(b.amount),
                    'team_id': str(b.team.id),
                    'team_name': t_name,
                    'short_name': s_name,
                    'bid_type': getattr(b, 'bid_type', 'Team Button'),
                    'created_at': b.created_at.isoformat(),
                })
            
            if bids_history:
                highest_bid = bids_history[0]

            player_data = {
                'id': str(active_player.id),
                'player_name': active_player.player.full_name or active_player.player.first_name if active_player.player else "Player",
                'serial_no': active_player.serial_no or 1,
                'category': active_player.category or "General",
                'role': active_player.role or "All-Rounder",
                'batting_style': active_player.batting_style or "Right Hand Bat",
                'bowling_style': active_player.bowling_style or "Right Arm Medium",
                'location': active_player.location or "",
                'base_price': float(active_player.base_price or 0),
                'photo_url': active_player.photo_url or "",
                'status': active_player.status,
                'custom_data': active_player.custom_data or {},
            }

        teams_financials = []
        for team in auction.teams.select_related('team').all():
            fin = team_financials(auction, team, active_player.id if active_player else None)
            teams_financials.append(fin)

        config = getattr(auction, 'v24_config', None)
        design = getattr(auction, 'page_design', None)

        return {
            'auction_id': str(auction.id),
            'auction_name': auction.name,
            'status': auction.status,
            'active_player': player_data,
            'current_bid': highest_bid['amount'] if highest_bid else (player_data['base_price'] if player_data else 0),
            'highest_bid': highest_bid,
            'bid_history': bids_history,
            'teams': teams_financials,
            'config': {
                'max_squad': config.max_squad if config else 11,
                'timer_seconds': config.timer_seconds if config else 30,
                'closing_wait_seconds': config.closing_wait_seconds if config else 5,
                'online_timer_enabled': config.online_timer_enabled if config else False,
                'sold_animation': config.sold_animation if config else True,
                'sold_animation_style': config.sold_animation_style if config else 'Confetti Burst',
                'sold_animation_duration': config.sold_animation_duration if config else 3,
                'highest_bid_animation': config.highest_bid_animation if config else True,
                'highest_bid_animation_style': config.highest_bid_animation_style if config else 'Fireworks',
                'highest_bid_animation_duration': config.highest_bid_animation_duration if config else 5,
                'sound_effects': config.sound_effects if config else True,
                'completion_message': config.completion_message if config else 'Auction Completed - All teams are now completed',
                'sold_animation_custom': (design.design_json.get('setup_rules_extended', {}).get('sold_animation_custom', '')) if design and design.design_json else '',
                'highest_bid_animation_custom': (design.design_json.get('setup_rules_extended', {}).get('highest_bid_animation_custom', '')) if design and design.design_json else '',
            } if config else {},
            'design': design.design_json if design else {},
        }

    @staticmethod
    def place_bid(auction, team, amount=None, is_custom=False):
        """
        Places a bid with authoritative Max Bid and slab verification.
        """
        player = auction.active_player
        if not player or player.status != 'BIDDING':
            return False, "No player is currently on the auction block."

        allowed, reason = allowed_team_for_lot(auction, team, player)
        if not allowed:
            return False, reason

        current_highest = player.bids.order_by('-amount').first()
        current_amount = current_highest.amount if current_highest else Decimal('0.00')

        config = getattr(auction, 'v24_config', None)
        allow_multiple = getattr(config, 'allow_multiple_bids', False) if config else False

        if not allow_multiple and current_highest and current_highest.team_id == team.id:
            return False, f"{team.team.name} is already the highest bidder."

        if amount is not None:
            bid_amount = Decimal(str(amount))
            valid, inc, reason = valid_custom_bid(auction, current_amount, bid_amount, player.base_price)
            if not valid:
                return False, reason
            bid_type = 'Custom Bid'
        else:
            if current_amount <= Decimal('0.00'):
                bid_amount = player.base_price
            else:
                inc = bid_increment(auction, current_amount)
                bid_amount = current_amount + inc
            bid_type = 'Team Button'

        # Check server-side Max Bid limit
        fin = team_financials(auction, team, player.id)
        if bid_amount > Decimal(str(fin['max_bid'])):
            return False, f"Team {fin['short_name']} cannot bid ₹{bid_amount:,.0f} as Max Bid limit (₹{fin['max_bid']:,.0f}) would be breached."

        with transaction.atomic():
            bid = Bid.objects.create(
                auction_player=player,
                team=team,
                amount=bid_amount,
                bid_type=bid_type
            )
            AuctionEventLog.objects.create(
                auction=auction,
                lot_player=player,
                team=team,
                event_type='BID',
                amount=bid_amount,
                details={'bid_type': bid_type}
            )

        return True, bid

    @staticmethod
    def sell_active_player(auction):
        """
        HAMMER DOWN: Sells active player to highest bidder.
        Deducts purse balance, creates purse transaction, and logs event.
        """
        player = auction.active_player
        if not player or player.status != 'BIDDING':
            return False, "No player is currently on the auction block."

        highest_bid = player.bids.order_by('-amount').first()
        if not highest_bid:
            return False, "A valid bidder and bid amount are required before marking player SOLD."

        team = highest_bid.team
        amount = highest_bid.amount

        with transaction.atomic():
            team.remaining_budget -= amount
            team.save()

            player.sold_to = team
            player.sold_price = amount
            player.status = 'SOLD'
            player.save()

            # Record purse ledger transaction
            TeamPurseTransaction.objects.create(
                auction=auction,
                team=team,
                player=player,
                transaction_type='Sale',
                amount=-amount,
                note=f"Auction sale of {player.player.full_name or 'Player'}"
            )

            AuctionEventLog.objects.create(
                auction=auction,
                lot_player=player,
                team=team,
                event_type='SOLD',
                amount=amount
            )

            auction.active_player = None
            auction.save()

        return True, player

    @staticmethod
    def unsold_active_player(auction):
        """
        Marks active player as UNSOLD.
        """
        player = auction.active_player
        if not player:
            return False, "No player is currently on the auction block."

        with transaction.atomic():
            player.status = 'UNSOLD'
            player.save()

            AuctionEventLog.objects.create(
                auction=auction,
                lot_player=player,
                event_type='UNSOLD',
                amount=Decimal('0.00')
            )

            auction.active_player = None
            auction.save()

        return True, player

    @staticmethod
    def undo_sale(auction):
        """
        Reverses the most recent SOLD player sale:
        - Refunds purse to franchise team
        - Sets player back to AVAILABLE (or BIDDING on block)
        - Logs UNDO_SALE transaction in ledger
        """
        last_sold = auction.players.filter(status='SOLD').order_by('-updated_at').first()
        if not last_sold or not last_sold.sold_to or not last_sold.sold_price:
            return False, "No active player sale found to undo."

        team = last_sold.sold_to
        refund_amount = last_sold.sold_price

        with transaction.atomic():
            team.remaining_budget += refund_amount
            team.save()

            TeamPurseTransaction.objects.create(
                auction=auction,
                team=team,
                player=last_sold,
                transaction_type='Undo Sale',
                amount=refund_amount,
                note=f"Undo Sale of {last_sold.player.full_name or 'Player'}"
            )

            last_sold.sold_to = None
            last_sold.sold_price = None
            last_sold.status = 'BIDDING'
            last_sold.save()

            # Restore on block
            auction.active_player = last_sold
            auction.save()

            AuctionEventLog.objects.create(
                auction=auction,
                lot_player=last_sold,
                team=team,
                event_type='UNDO_SALE',
                amount=refund_amount
            )

        return True, last_sold

    @staticmethod
    def undo_bid(auction):
        """
        Removes the latest bid placed on the active player.
        """
        player = auction.active_player
        if not player:
            return False, "No player on block."

        last_bid = player.bids.order_by('-created_at').first()
        if not last_bid:
            return False, "No bids to undo."

        with transaction.atomic():
            team = last_bid.team
            amount = last_bid.amount
            last_bid.delete()

            AuctionEventLog.objects.create(
                auction=auction,
                lot_player=player,
                team=team,
                event_type='UNDO_BID',
                amount=amount
            )

        return True, "Bid undone."

    @staticmethod
    def reset_bid(auction):
        """
        Resets all bids for current player on block back to 0.
        """
        player = auction.active_player
        if not player:
            return False, "No player on block."

        with transaction.atomic():
            player.bids.all().delete()
            AuctionEventLog.objects.create(
                auction=auction,
                lot_player=player,
                event_type='RESET_BID'
            )

        return True, "Bids reset."

    @staticmethod
    def select_player_by_number(auction, serial_no):
        """
        Puts a specific player on block by serial_no.
        """
        player = auction.players.filter(serial_no=serial_no, status__in=['AVAILABLE', 'PENDING', 'UNSOLD']).first()
        if not player:
            return False, f"Player with Serial No. {serial_no} is not available."

        with transaction.atomic():
            if auction.active_player and auction.active_player.id != player.id:
                if auction.active_player.status == 'BIDDING':
                    auction.active_player.status = 'AVAILABLE'
                    auction.active_player.save()

            player.status = 'BIDDING'
            player.save()

            auction.active_player = player
            if auction.status != 'ACTIVE':
                auction.status = 'ACTIVE'
            auction.save()

            AuctionEventLog.objects.create(
                auction=auction,
                lot_player=player,
                event_type='PLAYER_SELECTED',
                details={'method': 'MANUAL_SERIAL_NO', 'serial_no': serial_no}
            )

        return True, player

    @staticmethod
    def select_player_by_id(auction, player_id):
        """
        Puts a specific player on block by player ID.
        """
        player = auction.players.filter(id=player_id, status__in=['AVAILABLE', 'PENDING', 'UNSOLD']).first()
        if not player:
            return False, "Player is not available for auction."

        with transaction.atomic():
            if auction.active_player and auction.active_player.id != player.id:
                if auction.active_player.status == 'BIDDING':
                    auction.active_player.status = 'AVAILABLE'
                    auction.active_player.save()

            player.status = 'BIDDING'
            player.save()

            auction.active_player = player
            if auction.status != 'ACTIVE':
                auction.status = 'ACTIVE'
            auction.save()

            AuctionEventLog.objects.create(
                auction=auction,
                lot_player=player,
                event_type='PLAYER_SELECTED',
                details={'method': 'MANUAL_ID', 'player_id': str(player_id)}
            )

        return True, player

    @staticmethod
    def select_next_player_by_category(auction, category=None):
        """
        Puts the next available player on block, strictly respecting category priority or specific filter.
        """
        player = None
        if category and category.strip() and category.upper() != 'ALL':
            qs = auction.players.filter(status__in=['AVAILABLE', 'PENDING'], category__iexact=category.strip())
            player = qs.order_by('serial_no', 'created_at', 'id').first()
        else:
            # Respect category priority order configured in Master Setup & Rules
            cat_names = list(AuctionCategory.objects.filter(auction=auction).order_by('priority', 'display_order', 'created_at').values_list('name', flat=True))
            for cat_name in cat_names:
                cat_qs = auction.players.filter(status__in=['AVAILABLE', 'PENDING'], category__iexact=cat_name).order_by('serial_no', 'created_at', 'id')
                if cat_qs.exists():
                    player = cat_qs.first()
                    break
            if not player:
                player = auction.players.filter(status__in=['AVAILABLE', 'PENDING']).order_by('serial_no', 'created_at', 'id').first()

        if not player:
            # Fallback check for UNSOLD if bring_back_unsold is enabled
            config = getattr(auction, 'v24_config', None)
            bring_back = config.bring_back_unsold if config else True
            if bring_back:
                if category and category.strip() and category.upper() != 'ALL':
                    unsold_qs = auction.players.filter(status='UNSOLD', category__iexact=category.strip())
                    player = unsold_qs.order_by('serial_no', 'created_at', 'id').first()
                else:
                    cat_names = list(AuctionCategory.objects.filter(auction=auction).order_by('priority', 'display_order', 'created_at').values_list('name', flat=True))
                    for cat_name in cat_names:
                        cat_qs = auction.players.filter(status='UNSOLD', category__iexact=cat_name).order_by('serial_no', 'created_at', 'id')
                        if cat_qs.exists():
                            player = cat_qs.first()
                            break
                    if not player:
                        player = auction.players.filter(status='UNSOLD').order_by('serial_no', 'created_at', 'id').first()

        if not player:
            if category and category.strip() and category.upper() != 'ALL':
                return False, f"No available players found in category '{category}'."
            return False, "No available players remaining in the auction pool."

        with transaction.atomic():
            if auction.active_player and auction.active_player.id != player.id:
                if auction.active_player.status == 'BIDDING':
                    auction.active_player.status = 'AVAILABLE'
                    auction.active_player.save()

            player.status = 'BIDDING'
            player.save()

            auction.active_player = player
            if auction.status != 'ACTIVE':
                auction.status = 'ACTIVE'
            auction.save()

            AuctionEventLog.objects.create(
                auction=auction,
                lot_player=player,
                event_type='PLAYER_SELECTED',
                details={'method': 'CATEGORY_SELECT', 'category': category or 'ALL', 'player_id': str(player.id)}
            )

        return True, player

    @staticmethod
    def start_reauction_round(auction, category=None):
        """
        Brings back unsold players for re-auction.
        """
        unsold_qs = auction.players.filter(status='UNSOLD')
        if category:
            unsold_qs = unsold_qs.filter(category__iexact=category)

        count = unsold_qs.count()
        if count == 0:
            return False, "No unsold players available for re-auction."

        with transaction.atomic():
            unsold_qs.update(status='AVAILABLE', reauction_round_seen=1)
            AuctionEventLog.objects.create(
                auction=auction,
                event_type='REAUCTION_STARTED',
                details={'category': category or 'ALL_UNSOLD', 'players_count': count}
            )

        return True, f"Re-auction round started with {count} players."
