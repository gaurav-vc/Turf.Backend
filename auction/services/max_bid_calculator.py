"""
Max Bid Calculator & Squad Dynamic Programming Engine
Ported from Cricket Auction Phase 2 V24 authoritative logic.
"""
from decimal import Decimal
import json

def net_kitty(auction, team):
    """
    Net Kitty = Base Purse + Additional Kitty - Penalty Amount
    """
    config = getattr(auction, 'v24_config', None)
    base = team.remaining_budget
    # If base purse is set on auction config
    if config and config.additional_kitty:
        base += config.additional_kitty
    if config and config.penalty_amount:
        base -= config.penalty_amount
    
    # Team-level adjustments
    if hasattr(team, 'additional_kitty') and team.additional_kitty:
        base += team.additional_kitty
    if hasattr(team, 'penalty_amount') and team.penalty_amount:
        base -= team.penalty_amount
        
    return max(Decimal('0.00'), base)

def bid_increment(auction, current_bid):
    """
    Looks up the bid slab ladder for the given auction.
    """
    slabs = auction.bid_slabs.all().order_by('up_to_bid')
    if not slabs.exists():
        # Default increment
        if current_bid < Decimal('1000000'):
            return Decimal('50000')
        elif current_bid < Decimal('2000000'):
            return Decimal('100000')
        else:
            return Decimal('200000')
    
    for s in slabs:
        if current_bid < s.up_to_bid:
            return s.increment
    return slabs.last().increment

def valid_custom_bid(auction, current_bid, amount, base_price):
    """
    Validates custom bid against current bid and increment slab.
    """
    current_bid = Decimal(str(current_bid or 0))
    amount = Decimal(str(amount or 0))
    base_price = Decimal(str(base_price or 0))

    if current_bid <= 0:
        if amount == base_price:
            return True, base_price, "Valid first bid."
        return False, base_price, f"First bid must be exactly the base price ₹{base_price:,.0f}."

    inc = bid_increment(auction, current_bid)
    if inc <= 0:
        inc = Decimal('1000')

    diff = amount - current_bid
    if amount > current_bid and (diff % inc) == 0:
        return True, inc, "Valid custom bid."
    
    return False, inc, f"Enter a bid above ₹{current_bid:,.0f} in multiples of ₹{inc:,.0f}."

def squad_rule_value(player, field_key):
    """
    Extracts attribute value from player standard fields or custom_data.
    """
    key = str(field_key or '').strip().lower()
    if key == 'category':
        return str(player.category or '').strip()
    if key == 'role':
        return str(player.role or '').strip()
    if key == 'batting_style':
        return str(player.batting_style or '').strip()
    if key == 'bowling_style':
        return str(player.bowling_style or '').strip()
    if key == 'location':
        return str(player.location or '').strip()
    
    # Check custom_data
    custom = player.custom_data or {}
    if isinstance(custom, str):
        try:
            custom = json.loads(custom)
        except Exception:
            custom = {}
    return str(custom.get(field_key, '') or '').strip()

def team_category_counts(auction, team):
    """
    Counts how many players from each category the team has already bought.
    """
    sold_players = auction.players.filter(sold_to=team, status='SOLD')
    counts = {}
    for p in sold_players:
        cat = (p.category or 'General').strip().lower()
        counts[cat] = counts.get(cat, 0) + 1
    return counts

def team_rule_counts(auction, team):
    """
    Counts current acquisitions matching active squad rules.
    """
    sold_players = auction.players.filter(sold_to=team, status='SOLD')
    rules = auction.squad_rules.filter(active=True)
    out = {}
    for r in rules:
        key = (r.field_key.strip().lower(), r.field_value.strip().lower())
        out[key] = sum(1 for p in sold_players if squad_rule_value(p, r.field_key).lower() == key[1])
    return out

def team_rule_violation(auction, team, player):
    """
    Verifies if buying this player breaches any squad rule limits.
    """
    sold_players = list(auction.players.filter(sold_to=team, status='SOLD'))
    rules = auction.squad_rules.filter(active=True)
    for rule in rules:
        val = rule.field_value.strip().lower()
        pv = squad_rule_value(player, rule.field_key).lower()
        count = sum(1 for p in sold_players if squad_rule_value(p, rule.field_key).lower() == val)
        if rule.max_count is not None and count >= rule.max_count and pv == val:
            return False, f"Team has already reached the maximum {rule.field_key} requirement of {rule.max_count} for '{rule.field_value}'."
    return True, ""

def allowed_team_for_lot(auction, team, player):
    """
    Checks both category targets and squad rules for eligibility.
    """
    # Category quota check
    cat_name = (player.category or '').strip().lower()
    cat_obj = auction.categories.filter(name__iexact=cat_name).first()
    if cat_obj and cat_obj.target_count > 0:
        counts = team_category_counts(auction, team)
        bought = counts.get(cat_name, 0)
        if bought >= cat_obj.target_count:
            return False, f"Team has already acquired all required {cat_obj.target_count} player(s) for category '{cat_obj.name}'."

    # Squad rule checks
    ok, reason = team_rule_violation(auction, team, player)
    if not ok:
        return False, reason

    return True, None

def team_required_attribute_cost(auction, team, current_player_id=None):
    """
    Calculates the minimum base-cost reserve for remaining category and squad rules
    using a bounded 0/1 dynamic program (from Phase 2 V24).
    """
    categories = list(auction.categories.all())
    if not categories:
        return Decimal('0.00')

    cat_counts = team_category_counts(auction, team)
    cat_need = []
    for c in categories:
        target = c.target_count
        bought = cat_counts.get(c.name.strip().lower(), 0)
        n = max(0, target - bought)
        if n > 0:
            cat_need.append((c.name.strip().lower(), n))

    current_player = None
    if current_player_id:
        current_player = auction.players.filter(id=current_player_id).first()
    
    if current_player:
        cv = (current_player.category or '').strip().lower()
        for i, (name, n) in enumerate(cat_need):
            if name == cv and n > 0:
                cat_need[i] = (name, n - 1)
                break

    rules = list(auction.squad_rules.filter(active=True))
    rule_counts = team_rule_counts(auction, team)
    rule_need = []
    for r in rules:
        val = r.field_value.strip().lower()
        min_c = r.min_count
        cur_c = rule_counts.get((r.field_key.strip().lower(), val), 0)
        n = max(0, min_c - cur_c)
        if current_player and n > 0 and squad_rule_value(current_player, r.field_key).lower() == val:
            n -= 1
        if n > 0:
            rule_need.append((r.field_key.strip().lower(), val, n))

    cat_need = [x for x in cat_need if x[1] > 0]
    if not cat_need and not rule_need:
        return Decimal('0.00')

    total_slots = sum(n for _, n in cat_need)
    if total_slots <= 0:
        total_slots = sum(n for _, _, n in rule_need)

    available_players = auction.players.filter(status__in=['AVAILABLE', 'UNSOLD'])
    if current_player_id:
        available_players = available_players.exclude(id=current_player_id)
    
    p_rows = sorted(list(available_players), key=lambda p: p.base_price or Decimal('0.00'))

    cat_names = [x[0] for x in cat_need]
    cat_limits = [x[1] for x in cat_need]
    rule_keys = [(x[0], x[1]) for x in rule_need]
    rule_limits = [x[2] for x in rule_need]

    start_state = tuple([0] * len(cat_limits) + [0] * len(rule_limits))
    dp = {start_state: Decimal('0.00')}
    max_states = 10000

    for p in p_rows:
        additions = [0] * len(start_state)
        cv = (p.category or '').strip().lower()
        if cv in cat_names:
            additions[cat_names.index(cv)] = 1
        for i, (fk, fv) in enumerate(rule_keys):
            if squad_rule_value(p, fk).lower() == fv:
                additions[len(cat_limits) + i] = 1
        if not any(additions):
            continue

        snapshot = list(dp.items())
        for state, cost in snapshot:
            if sum(state) >= total_slots:
                continue
            ns = list(state)
            for i, a in enumerate(additions):
                if a:
                    ns[i] = min((cat_limits + rule_limits)[i], ns[i] + a)
            ns = tuple(ns)
            nc = cost + (p.base_price or Decimal('0.00'))
            if nc < dp.get(ns, Decimal('1000000000.00')):
                dp[ns] = nc

        if len(dp) > max_states:
            dp = dict(sorted(dp.items(), key=lambda kv: kv[1])[:max_states])

    target = tuple(cat_limits + rule_limits)
    if target in dp:
        return dp[target]

    # Fallback to category base reserve
    cat_only = Decimal('0.00')
    for name, n in cat_need:
        c_obj = next((c for c in categories if c.name.strip().lower() == name), None)
        price = c_obj.base_price if c_obj else Decimal('1000.00')
        cat_only += Decimal(n) * price

    return cat_only

def team_financials(auction, team, current_player_id=None):
    """
    Computes real-time financials: kitty, spent, balance, future_base_cost, reserve, max_bid.
    Formula: Max Bid = Net Kitty - (Spent + Future Base Cost + Reserve)
    """
    config = getattr(auction, 'v24_config', None)
    reserve = Decimal(str(config.reserve_amount)) if config else Decimal('0.00')
    if hasattr(team, 'reserve_amount') and team.reserve_amount:
        reserve = Decimal(str(team.reserve_amount))

    kitty = net_kitty(auction, team)

    # Spent
    sold_to_team = auction.players.filter(sold_to=team, status='SOLD')
    spent = sum((p.sold_price or Decimal('0.00') for p in sold_to_team), Decimal('0.00'))
    bought_count = sold_to_team.count()

    balance = max(Decimal('0.00'), kitty - spent)

    # Future base cost calculation
    cat_counts = team_category_counts(auction, team)
    remaining_base_cost = Decimal('0.00')
    pending_slots = 0
    for c in auction.categories.all():
        req = c.target_count
        bought = cat_counts.get(c.name.strip().lower(), 0)
        rem = max(0, req - bought)
        pending_slots += rem
        remaining_base_cost += Decimal(rem) * c.base_price

    cur_base = Decimal('0.00')
    if current_player_id:
        cp = auction.players.filter(id=current_player_id).first()
        if cp:
            cur_base = cp.base_price or Decimal('0.00')

    rule_cost = team_required_attribute_cost(auction, team, current_player_id)
    future_base_cost = max(Decimal('0.00'), remaining_base_cost - cur_base, rule_cost)

    max_bid = max(Decimal('0.00'), kitty - (spent + future_base_cost + reserve))

    t_logo = ''
    if team.team and getattr(team.team, 'logo', None):
        try:
            t_logo = team.team.logo.url
        except Exception:
            pass

    t_name = team.team.name if team.team else 'Team'
    import re
    words = [w for w in re.split(r'[\s\-_]+', t_name) if w]
    auto_short = ("".join(w[0] for w in words)[:4].upper()) if len(words) >= 2 else t_name[:3].upper()
    cd = getattr(team, 'custom_data', {}) or {}
    s_name = cd.get('short_name') or getattr(team.team, 'short_name', None) or auto_short

    return {
        'team_id': str(team.id),
        'team_name': t_name,
        'short_name': s_name,
        'team_color': getattr(team.team, 'logo_color', '#3b82f6') if team.team else '#3b82f6',
        'team_logo': t_logo,
        'kitty': float(kitty),
        'spent': float(spent),
        'balance': float(balance),
        'reserve': float(reserve),
        'future_base_cost': float(future_base_cost),
        'max_bid': float(max_bid),
        'bought': bought_count,
        'pending': pending_slots,
        'category_counts': cat_counts,
    }
