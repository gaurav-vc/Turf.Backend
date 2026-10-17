import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from sports.models import Sport

sports_data = [
    {
        'name': 'Box Cricket',
        'slug': 'box-cricket',
        'team_size_min': 6,
        'team_size_max': 11,
        'scoring_engine': 'runs_wickets',
        'default_rules': {'overs': 6, 'format': 'Box'},
        'roles': ['Batsman', 'Bowler', 'All-Rounder', 'Wicket-Keeper']
    },
    {
        'name': 'Football (5-a-side)',
        'slug': 'football-5',
        'team_size_min': 5,
        'team_size_max': 8,
        'scoring_engine': 'goals',
        'default_rules': {'duration_minutes': 40, 'substitutes': 3, 'halves': 2},
        'roles': ['Forward', 'Midfielder', 'Defender', 'Goalkeeper']
    },
    {
        'name': 'Football (7-a-side)',
        'slug': 'football-7',
        'team_size_min': 7,
        'team_size_max': 10,
        'scoring_engine': 'goals',
        'default_rules': {'duration_minutes': 60, 'substitutes': 3, 'halves': 2},
        'roles': ['Forward', 'Midfielder', 'Defender', 'Goalkeeper']
    },
    {
        'name': 'Futsal',
        'slug': 'futsal',
        'team_size_min': 5,
        'team_size_max': 12,
        'scoring_engine': 'goals',
        'default_rules': {'duration_minutes': 40, 'halves': 2, 'substitutes': 7},
        'roles': ['Pivot', 'Flank', 'Defender', 'Goalkeeper']
    },
    {
        'name': 'Tennis (Singles)',
        'slug': 'tennis-singles',
        'team_size_min': 1,
        'team_size_max': 1,
        'scoring_engine': 'sets_games_points',
        'default_rules': {'sets': 3, 'format': 'Singles'},
        'roles': ['Player']
    },
    {
        'name': 'Tennis (Doubles)',
        'slug': 'tennis-doubles',
        'team_size_min': 2,
        'team_size_max': 2,
        'scoring_engine': 'sets_games_points',
        'default_rules': {'sets': 3, 'format': 'Doubles'},
        'roles': ['Server', 'Receiver']
    },
    {
        'name': 'Badminton (Singles)',
        'slug': 'badminton-singles',
        'team_size_min': 1,
        'team_size_max': 1,
        'scoring_engine': 'points_sets',
        'default_rules': {'sets': 3, 'points_per_set': 21},
        'roles': ['Player']
    },
    {
        'name': 'Badminton (Doubles)',
        'slug': 'badminton-doubles',
        'team_size_min': 2,
        'team_size_max': 2,
        'scoring_engine': 'points_sets',
        'default_rules': {'sets': 3, 'points_per_set': 21},
        'roles': ['Player']
    },
    {
        'name': 'Volleyball',
        'slug': 'volleyball',
        'team_size_min': 6,
        'team_size_max': 12,
        'scoring_engine': 'sets_points',
        'default_rules': {'sets': 5, 'points_per_set': 25},
        'roles': ['Setter', 'Outside Hitter', 'Middle Blocker', 'Opposite Hitter', 'Libero']
    },
    {
        'name': 'Hockey',
        'slug': 'hockey',
        'team_size_min': 11,
        'team_size_max': 16,
        'scoring_engine': 'goals',
        'default_rules': {'duration_minutes': 60, 'quarters': 4, 'substitutes': 5},
        'roles': ['Forward', 'Midfielder', 'Defender', 'Goalkeeper']
    },
    {
        'name': 'Kabaddi',
        'slug': 'kabaddi',
        'team_size_min': 7,
        'team_size_max': 12,
        'scoring_engine': 'points',
        'default_rules': {'duration_minutes': 40, 'halves': 2},
        'roles': ['Raider', 'Defender', 'All-Rounder']
    },
    {
        'name': 'Pickleball (Singles)',
        'slug': 'pickleball-singles',
        'team_size_min': 1,
        'team_size_max': 1,
        'scoring_engine': 'points',
        'default_rules': {'points_to_win': 11},
        'roles': ['Player']
    },
    {
        'name': 'Pickleball (Doubles)',
        'slug': 'pickleball-doubles',
        'team_size_min': 2,
        'team_size_max': 2,
        'scoring_engine': 'points',
        'default_rules': {'points_to_win': 11},
        'roles': ['Server', 'Receiver']
    },
    {
        'name': 'Ultimate Frisbee',
        'slug': 'ultimate-frisbee',
        'team_size_min': 7,
        'team_size_max': 14,
        'scoring_engine': 'points',
        'default_rules': {'points_to_win': 15},
        'roles': ['Handler', 'Cutter']
    },
    {
        'name': 'Throwball',
        'slug': 'throwball',
        'team_size_min': 7,
        'team_size_max': 12,
        'scoring_engine': 'points_sets',
        'default_rules': {'sets': 3, 'points_per_set': 25},
        'roles': ['Server', 'Attacker', 'Defender']
    }
]

for sd in sports_data:
    Sport.objects.get_or_create(slug=sd['slug'], defaults=sd)

print("Sports seeded successfully!")
