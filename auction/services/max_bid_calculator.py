"""
V24 MAX BID LOGIC & SQUAD DYNAMIC PROGRAMMING ENGINE
Authoritative Implementation conforming to:
Cricket_Auction_Phase2_V24_ALL_REQUIREMENTS(2).zip

Core Formula:
  Net Kitty = Team Purse + Team Additional Kitty − Team Penalty
  Future Mandatory Cost = max(Category Reserve Excluding Current Player, Rule-Aware Minimum-Cost Reserve)
  Max Bid = Net Kitty − [Spent + Future Mandatory Cost + Team Reserve]
  Clamped with max(0, ...)
"""
from decimal import Decimal
import json
import re


def assumed_current_base(auction):
    """
    Step 10: Pre-Auction / No Current Lot Assumption.
    When there is no current lot, team_financials() obtains an assumed current base:
    - For category-wise auctions: uses the base price of the last category in category_sequence.
    - For open auctions: uses the last category returned by category_rows().
    """
    config = getattr(auction, 'v24_config', None)
    categories = list(auction.categories.all())
    if not categories:
        return Decimal('0.00')

    # Category-wise auction
    if config and config.category_wise_bidding and config.category_sequence:
        seq = config.category_sequence
        if isinstance(seq, list) and len(seq) > 0:
            last_cat_name = str(seq[-1]).strip().lower()
            matching = [c for c in categories if c.name.strip().lower() == last_cat_name]
            if matching:
                return matching[0].base_price or Decimal('0.00')

    # Open auction or fallback: last category in display order / priority
    return categories[-1].base_price or Decimal('0.00')


def net_kitty(auction, team):
    """
    Step 4: Calculate Net Kitty
    Net Kitty = Team Purse + Team Additional Kitty - Team Penalty
    Team Purse is the base budget allocated to the team.
    """
    # 1. Base team purse
    base_purse = None
    cd = getattr(team, 'custom_data', {}) or {}
    if isinstance(cd, dict) and cd.get('base_purse'):
        try:
            base_purse = Decimal(str(cd['base_purse']))
        except Exception:
            pass

    if base_purse is None:
        if getattr(auction, 'base_budget', None):
            base_purse = Decimal(str(auction.base_budget))
        else:
            # Fallback to wallet remaining + already spent
            sold_to_team = auction.players.filter(sold_to=team, status='SOLD')
            spent = sum((p.sold_price or Decimal('0.00') for p in sold_to_team), Decimal('0.00'))
            base_purse = (team.remaining_budget or Decimal('0.00')) + spent

    # 2. Team-specific financial adjustments
    additional = Decimal(str(getattr(team, 'additional_kitty', 0) or 0))
    penalty = Decimal(str(getattr(team, 'penalty_amount', 0) or 0))

    calc = base_purse + additional - penalty
    return max(Decimal('0.00'), calc)


def team_category_counts(auction, team):
    """
    Step 2 & 6: Counts how many players from each category the team has already bought.
    """
    sold_players = auction.players.filter(sold_to=team, status='SOLD')
    counts = {}
    for p in sold_players:
        cat = (p.category or 'General').strip().lower()
        counts[cat] = counts.get(cat, 0) + 1
    return counts


def remaining_base_cost(auction, team):
    """
    Step 6: Calculate remaining category base cost before current player.
    Loops through every configured tournament category.
    remaining = max(0, target_count - team_bought_count)
    adds remaining * category_base_price.
    """
    cat_counts = team_category_counts(auction, team)
    total_cost = Decimal('0.00')
    cat_needs = []

    for c in auction.categories.all():
        req = c.target_count or 0
        bought = cat_counts.get(c.name.strip().lower(), 0)
        rem = max(0, req - bought)
        price = c.base_price or Decimal('0.00')
        total_cost += Decimal(rem) * price
        if rem > 0:
            cat_needs.append((c.name.strip().lower(), rem, price))

    return total_cost, cat_needs


def squad_rule_value(player, field_key):
    """
    Reads a player's attribute value for a standard or custom squad-rule field.
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
    if key == 'age':
        return str(player.age if player.age is not None else '').strip()
    if key == 'mobile':
        return str(player.mobile or '').strip()

    # Check custom_data
    custom = player.custom_data or {}
    if isinstance(custom, str):
        try:
            custom = json.loads(custom)
        except Exception:
            custom = {}
    return str(custom.get(field_key, '') or custom.get(key, '') or '').strip()


def team_rule_counts(auction, team):
    """
    Step 8: Counts a team's current players against all active squad rules.
    """
    sold_players = list(auction.players.filter(sold_to=team, status='SOLD'))
    rules = list(auction.squad_rules.filter(active=True))
    out = {}
    for r in rules:
        fk = r.field_key.strip().lower()
        fv = r.field_value.strip().lower()
        key = (fk, fv)
        out[key] = sum(1 for p in sold_players if squad_rule_value(p, r.field_key).lower() == fv)
    return out


def team_rule_violation(auction, team, player):
    """
    Step 2: Stops a team exceeding a squad-rule maximum.
    """
    sold_players = list(auction.players.filter(sold_to=team, status='SOLD'))
    rules = list(auction.squad_rules.filter(active=True))

    for rule in rules:
        val = rule.field_value.strip().lower()
        pv = squad_rule_value(player, rule.field_key).lower()
        count = sum(1 for p in sold_players if squad_rule_value(p, rule.field_key).lower() == val)
        if rule.max_count is not None and count >= rule.max_count and pv == val:
            return False, f"Team has already reached the maximum {rule.field_key} requirement of {rule.max_count} for '{rule.field_value}'."
    return True, ""


def allowed_team_for_lot(auction, team, player):
    """
    Step 2: Checks category quota and squad-rule eligibility.
    Team eligibility and Max Bid are separate controls.
    """
    # 1. Category quota check
    cat_name = (player.category or '').strip().lower()
    cat_obj = auction.categories.filter(name__iexact=cat_name).first()
    if cat_obj and cat_obj.target_count > 0:
        counts = team_category_counts(auction, team)
        bought = counts.get(cat_name, 0)
        if bought >= cat_obj.target_count:
            return False, f"Team has already acquired all required {cat_obj.target_count} player(s) for category '{cat_obj.name}'."

    # 2. Squad rule maximum violation check
    ok, reason = team_rule_violation(auction, team, player)
    if not ok:
        return False, reason

    return True, None


def bid_increment(auction, current_bid):
    """
    Step 3: Returns configured bid increment for current bid from bid_slabs.
    """
    slabs = auction.bid_slabs.all().order_by('up_to_bid')
    has_slabs = slabs.exists() if hasattr(slabs, 'exists') else bool(slabs)
    if not has_slabs:
        if current_bid < Decimal('1000000'):
            return Decimal('50000')
        elif current_bid < Decimal('2000000'):
            return Decimal('100000')
        else:
            return Decimal('200000')

    for s in slabs:
        if current_bid < s.up_to_bid:
            return s.increment
    return slabs.last().increment if hasattr(slabs, 'last') else slabs[-1].increment


def valid_custom_bid(auction, current_bid, amount, base_price):
    """
    Step 3: Validates custom bid amount / increment grid.
    First bid must equal base price; subsequent must be > current_bid and multiple of slab.
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


def get_ordered_categories(auction):
    """
    Returns categories ordered according to the tournament's configured category sequence,
    falling back to priority and display_order.
    """
    config = getattr(auction, 'v24_config', None)
    categories = list(auction.categories.all())
    if not categories:
        return []

    if config and getattr(config, 'category_sequence', None):
        seq = config.category_sequence
        if isinstance(seq, list) and len(seq) > 0:
            cat_map = {c.name.strip().lower(): c for c in categories}
            ordered = []
            for name in seq:
                nm = str(name).strip().lower()
                if nm in cat_map:
                    ordered.append(cat_map[nm])
            for c in categories:
                if c not in ordered:
                    ordered.append(c)
            return ordered

    def sort_key(c):
        p = getattr(c, 'priority', 1)
        p_val = int(p) if isinstance(p, (int, float)) else 1
        d = getattr(c, 'display_order', 1)
        d_val = int(d) if isinstance(d, (int, float)) else 1
        return (p_val, d_val, str(getattr(c, 'id', '')))

    return sorted(categories, key=sort_key)


def team_required_attribute_cost(auction, team, current_player_id=None):
    """
    Steps 6, 7, 8, 9, 10:
    Finds the minimum future reserve cost using bounded 0/1 Dynamic Programming.
    Combines:
      - Category-Reserve-Excluding-Current-Player (Steps 6 & 7)
      - Rule-Aware Minimum-Cost Reserve (Steps 8 & 9)
    Future Mandatory Cost = max(Category-Reserve-Excluding-Current-Player, Rule-Aware Minimum-Cost Reserve)

    Sequence Rule:
      - If current_player is on block and team still needs player(s) in current_player's category:
        deduct 1 unit from current_player.category.
      - If current_player is on block but team already bought the required number for that category:
        consider the base price of the NEXT to be auctioned category in sequence that this team still needs!
      - If no player is on the block (pre-auction or between lots):
        consider the base price of the FIRST category in sequence that this team still needs!
    """
    ordered_categories = get_ordered_categories(auction)
    current_player = None
    if current_player_id:
        current_player = auction.players.filter(id=current_player_id).first()

    # Step 6 & 7: Category needs & Category Reserve Excluding Current Player
    cat_counts = team_category_counts(auction, team)
    cat_rem = {}
    for c in ordered_categories:
        c_name = c.name.strip().lower()
        target = c.target_count or 0
        bought = cat_counts.get(c_name, 0)
        cat_rem[c_name] = max(0, target - bought)

    # Determine which category to deduct 1 unit from (current / next in sequence to be bought)
    deduct_cat_name = None
    if current_player:
        cp_cat = (current_player.category or '').strip().lower()
        if cat_rem.get(cp_cat, 0) > 0:
            # Case 1: Team still needs player(s) in current player's category
            deduct_cat_name = cp_cat
        else:
            # Case 2: Team already completed current category quota.
            # Look forward in the sequence for the NEXT category this team still needs!
            cp_idx = -1
            for idx, c in enumerate(ordered_categories):
                if c.name.strip().lower() == cp_cat:
                    cp_idx = idx
                    break
            candidates_forward = ordered_categories[cp_idx + 1:] if cp_idx >= 0 else []
            for c in candidates_forward:
                c_name = c.name.strip().lower()
                if cat_rem.get(c_name, 0) > 0:
                    deduct_cat_name = c_name
                    break
            # If none found forward, search from beginning of sequence
            if not deduct_cat_name:
                for c in ordered_categories:
                    c_name = c.name.strip().lower()
                    if cat_rem.get(c_name, 0) > 0:
                        deduct_cat_name = c_name
                        break
    else:
        # Case 3: Pre-auction or between lots (no current lot).
        # Consider the FIRST category in sequence that this team still needs!
        for c in ordered_categories:
            c_name = c.name.strip().lower()
            if cat_rem.get(c_name, 0) > 0:
                deduct_cat_name = c_name
                break

    # Apply 1-player deduction from the determined category
    if deduct_cat_name and cat_rem.get(deduct_cat_name, 0) > 0:
        cat_rem[deduct_cat_name] -= 1

    # Build cat_need and calculate Category-Reserve-Excluding-Current-Player
    cat_need = []
    category_reserve_excl_current = Decimal('0.00')
    for c in ordered_categories:
        c_name = c.name.strip().lower()
        rem = cat_rem.get(c_name, 0)
        price = c.base_price or Decimal('0.00')
        if rem > 0:
            cat_need.append((c_name, rem, price))
            category_reserve_excl_current += Decimal(rem) * price

    # Step 8: Squad rule needs excluding current player
    rules = list(auction.squad_rules.filter(active=True))
    rule_counts = team_rule_counts(auction, team)
    rule_need = []

    for r in rules:
        val = r.field_value.strip().lower()
        min_c = r.min_count or 0
        cur_c = rule_counts.get((r.field_key.strip().lower(), val), 0)
        rem_min = max(0, min_c - cur_c)
        # If current player satisfies this rule, remove one unit
        if current_player and rem_min > 0 and squad_rule_value(current_player, r.field_key).lower() == val:
            rem_min -= 1
        if rem_min > 0:
            rule_need.append((r.field_key.strip().lower(), val, rem_min))

    # If no further category or squad rule needs exist, future mandatory cost is 0
    if not cat_need and not rule_need:
        return Decimal('0.00')
    if not cat_need and not rule_need:
        return Decimal('0.00')

    # Step 9: Bounded 0/1 Dynamic Programming over eligible candidate players
    # Filter available/unsold players in this auction excluding the current lot player
    available_players = auction.players.filter(status__in=['AVAILABLE', 'UNSOLD'])
    if current_player_id:
        if hasattr(available_players, 'exclude'):
            available_players = available_players.exclude(id=current_player_id)
        else:
            available_players = [p for p in available_players if getattr(p, 'id', None) != current_player_id]

    # Sort candidates by base price ascending
    p_rows = sorted(list(available_players), key=lambda p: p.base_price or Decimal('0.00'))

    cat_names = [x[0] for x in cat_need]
    cat_limits = [x[1] for x in cat_need]
    rule_keys = [(x[0], x[1]) for x in rule_need]
    rule_limits = [x[2] for x in rule_need]

    total_target_slots = sum(cat_limits)
    if total_target_slots <= 0:
        total_target_slots = sum(rule_limits)

    start_state = tuple([0] * len(cat_limits) + [0] * len(rule_limits))
    target_state = tuple(cat_limits + rule_limits)
    dp = {start_state: Decimal('0.00')}
    max_states = 12000

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
        p_base = p.base_price or Decimal('0.00')

        for state, cost in snapshot:
            if state == target_state:
                continue

            ns = list(state)
            for i, a in enumerate(additions):
                if a:
                    ns[i] = min(target_state[i], ns[i] + a)
            ns = tuple(ns)
            nc = cost + p_base

            if nc < dp.get(ns, Decimal('100000000000.00')):
                dp[ns] = nc

        # Prune state space if needed
        if len(dp) > max_states:
            dp = dict(sorted(dp.items(), key=lambda kv: kv[1])[:max_states])

    # Rule-Aware Minimum-Cost Reserve
    rule_aware_reserve = dp.get(target_state, None)

    # Step 10: Combine the two reserve concepts
    # Future Mandatory Cost = max(Category Reserve Excluding Current Player, Rule-Aware Minimum-Cost Reserve)
    if rule_aware_reserve is not None:
        future_mandatory_cost = max(category_reserve_excl_current, rule_aware_reserve)
    else:
        # Fallback to category-only reserve if DP couldn't reach full intersection
        future_mandatory_cost = category_reserve_excl_current

    return future_mandatory_cost


def team_financials(auction, team, current_player_id=None):
    """
    Steps 4, 5, 10, 11, 12: Core V24 Financial & Max Bid Calculator.
    Net Kitty = Team Purse + Team Additional Kitty - Team Penalty
    Future Mandatory Cost = max(Category Reserve Excl Current, Rule-Aware DP Reserve)
    Max Bid = Net Kitty - [Spent + Future Mandatory Cost + Team Reserve]
    Clamped with max(0, ...)
    """
    # Step 4: Net Kitty
    kitty = net_kitty(auction, team)

    # Step 5: Calculate Spent (active player_sales / sold_players for this team)
    sold_to_team = auction.players.filter(sold_to=team, status='SOLD')
    spent = sum((p.sold_price or Decimal('0.00') for p in sold_to_team), Decimal('0.00'))
    bought_count = sold_to_team.count() if hasattr(sold_to_team, 'count') and not isinstance(sold_to_team, list) else len(sold_to_team)

    # Balance (wallet balance available)
    balance = max(Decimal('0.00'), kitty - spent)

    # Steps 6, 7, 8, 9, 10: Future Mandatory Cost
    future_mandatory_cost = team_required_attribute_cost(auction, team, current_player_id)

    # Step 11: Team Reserve (protected money)
    config = getattr(auction, 'v24_config', None)
    team_reserve = Decimal('0.00')
    if hasattr(team, 'reserve_amount') and team.reserve_amount:
        team_reserve = Decimal(str(team.reserve_amount))
    elif config and getattr(config, 'reserve_amount', None):
        team_reserve = Decimal(str(config.reserve_amount))

    # Step 12: Calculate Max Bid
    # Max Bid = Net Kitty − [Spent + Future Mandatory Cost + Team Reserve]
    raw_max_bid = kitty - (spent + future_mandatory_cost + team_reserve)
    max_bid = max(Decimal('0.00'), raw_max_bid)

    # Pending category quota slots count
    cat_counts = team_category_counts(auction, team)
    pending_slots = 0
    for c in auction.categories.all():
        req = c.target_count or 0
        bought = cat_counts.get(c.name.strip().lower(), 0)
        pending_slots += max(0, req - bought)

    # Team display metadata
    t_name = team.team.name if team.team else 'Team'
    words = [w for w in re.split(r'[\s\-_]+', t_name) if w]
    auto_short = ("".join(w[0] for w in words)[:4].upper()) if len(words) >= 2 else t_name[:3].upper()
    cd = getattr(team, 'custom_data', {}) or {}
    s_name = cd.get('short_name') or getattr(team.team, 'short_name', None) or auto_short

    t_logo = ''
    if team.team and getattr(team.team, 'logo', None):
        try:
            t_logo = team.team.logo.url
        except Exception:
            pass

    t_color = cd.get('color') or cd.get('team_color') or (team.team.logo_color if team.team and getattr(team.team, 'logo_color', None) else None) or getattr(team, 'color', None) or '#3b82f6'

    return {
        'team_id': str(team.id),
        'team_name': t_name,
        'short_name': s_name,
        'team_color': t_color,
        'color': t_color,
        'team_logo': t_logo,
        'kitty': float(kitty),
        'spent': float(spent),
        'balance': float(balance),
        'reserve': float(team_reserve),
        'future_base_cost': float(future_mandatory_cost),
        'max_bid': float(max_bid),
        'bought': bought_count,
        'pending': pending_slots,
        'category_counts': cat_counts,
        'max_squad': int(getattr(config, 'max_squad', 0) or 0) if config else 0,
    }
