import os
import django
from django.utils import timezone
import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from accounts.models import User
from turfs.models import Turf
from sports.models import Sport, Team, Player
from clubs.models import Club, ClubMember, ClubTournament, ClubMatch, LiveMatchTimerState, LiveCricketScorecard

def seed_demo_club():
    print("Seeding showcase Cricket Club and Match Day environment...")
    
    # 1. Get or create a sample user
    owner = User.objects.filter(user_type='PLAYER').first()
    if not owner:
        owner = User.objects.filter(is_superuser=True).first()
    if not owner:
        owner = User.objects.create_user(
            email='clubowner@example.com',
            username='clubowner',
            full_name='Captain Vikram',
            user_type='PLAYER'
        )

    co_owner = User.objects.filter(user_type='PLAYER').exclude(id=owner.id).first()
    if not co_owner:
        co_owner = User.objects.create_user(
            email='coadmin@example.com',
            username='coadmin',
            full_name='Rohit Sharma (Co-Admin)',
            user_type='PLAYER'
        )

    # 2. Get or create Box Cricket Sport
    sport, _ = Sport.objects.get_or_create(
        slug='box-cricket',
        defaults={
            'name': 'Box Cricket',
            'team_size_min': 6,
            'team_size_max': 11,
            'scoring_engine': 'runs_wickets'
        }
    )

    # 3. Get or create Turf
    home_turf = Turf.objects.first()

    # 4. Create Showcase Club
    club, created = Club.objects.get_or_create(
        name="Royal Challengers Turf Club",
        defaults={
            'description': "Premier turf cricket league club. Hosting fast-paced 7-a-side matches with official 13-minute innings.",
            'owner': owner,
            'home_turf': home_turf,
            'sport': sport,
            'theme_color': '#10b981',
            'privacy': 'PUBLIC',
            'invite_code': 'ROYAL777',
            'customization': {
                'default_inning_minutes': 13,
                'default_reminder_seconds': 120,
                'default_player_count': 7,
                'default_wickets_rule': 6,
                'pause_presets': [
                    {'name': 'Wicket Break', 'seconds': 20},
                    {'name': 'Ball Lost', 'seconds': 60},
                    {'name': 'Injury Break', 'seconds': 60},
                    {'name': 'Strategy Timeout', 'seconds': 90}
                ]
            }
        }
    )

    # 5. Add Owner & Co-Owner memberships
    ClubMember.objects.get_or_create(
        club=club,
        user=owner,
        defaults={'role': 'OWNER', 'is_active': True}
    )
    ClubMember.objects.get_or_create(
        club=club,
        user=co_owner,
        defaults={'role': 'CO_OWNER', 'is_active': True}
    )

    # 6. Create Teams & Players for Club Match
    team1, _ = Team.objects.get_or_create(
        name="Thunder Strikers",
        defaults={'user': owner, 'sport': sport, 'logo_color': '#10b981'}
    )
    team2, _ = Team.objects.get_or_create(
        name="Desert Warriors",
        defaults={'user': co_owner, 'sport': sport, 'logo_color': '#8b5cf6'}
    )

    # Add 7 players to each team
    t1_names = ["Virat K. (C)", "KL Rahul", "Surya K.", "Hardik P.", "Ravindra J.", "Jasprit B.", "Arshdeep S."]
    for idx, p_name in enumerate(t1_names):
        Player.objects.get_or_create(
            team=team1,
            name=p_name,
            defaults={'role': 'Batsman' if idx < 3 else 'All-Rounder' if idx < 5 else 'Bowler'}
        )

    t2_names = ["Rohit S. (C)", "Shubman G.", "Rishabh P.", "Axar P.", "Kuldeep Y.", "Mohammed S.", "Siraj M."]
    for idx, p_name in enumerate(t2_names):
        Player.objects.get_or_create(
            team=team2,
            name=p_name,
            defaults={'role': 'Batsman' if idx < 3 else 'All-Rounder' if idx < 5 else 'Bowler'}
        )

    # 7. Create Recurring Tournament (Jan 1, Jan 5, Jan 15, Jan 20)
    tournament, _ = ClubTournament.objects.get_or_create(
        club=club,
        name="Winter Premier Cup 2026",
        defaults={
            'description': "4-leg championship series played across January turf slots.",
            'status': 'UPCOMING',
            'is_recurring': True,
            'recurrence_type': 'CUSTOM_DATES',
            'recurrence_dates': ['2026-01-01', '2026-01-05', '2026-01-15', '2026-01-20'],
            'start_date': timezone.now() + datetime.timedelta(days=1)
        }
    )

    # 8. Create Scheduled Match with 7 players -> 6 wickets & 13-min inning timer
    match, _ = ClubMatch.objects.get_or_create(
        club=club,
        team1=team1,
        team2=team2,
        defaults={
            'tournament': tournament,
            'turf': home_turf,
            'match_date': timezone.now() + datetime.timedelta(hours=2),
            'round_name': 'Opening Derby (Leg 1)',
            'team1_players_count': 7,
            'team2_players_count': 7,
            'wickets_allowed': 6, # 7 players -> 6 wickets!
            'is_last_match': False,
            'status': 'SCHEDULED'
        }
    )

    # Timer State
    timer, _ = LiveMatchTimerState.objects.get_or_create(
        match=match,
        defaults={
            'inning_duration_seconds': 780, # 13 minutes
            'reminder_threshold_seconds': 120, # 2 minutes alert
            'is_running': False,
            'is_paused': False
        }
    )

    # Scorecard
    scorecard, _ = LiveCricketScorecard.objects.get_or_create(
        match=match,
        defaults={
            'batting_team': team1,
            'bowling_team': team2
        }
    )

    print(f"Successfully seeded Club: '{club.name}' (ID: {club.id})")
    print(f"Match ID: {match.id} (Status: {match.status})")

if __name__ == '__main__':
    seed_demo_club()
