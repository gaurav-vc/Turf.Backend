from django.db import models
from core.models import BaseModel

class Sport(BaseModel):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    icon = models.URLField(blank=True, null=True)
    team_size_min = models.IntegerField(default=1)
    team_size_max = models.IntegerField(default=11)
    scoring_engine = models.CharField(max_length=50)
    default_rules = models.JSONField(default=dict, blank=True)
    roles = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return self.name

class RuleSet(BaseModel):
    sport = models.ForeignKey(Sport, on_delete=models.CASCADE, related_name='rulesets')
    name = models.CharField(max_length=100)
    rules = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"{self.sport.name} - {self.name}"

from django.conf import settings

class Team(BaseModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='teams')
    sport = models.ForeignKey(Sport, on_delete=models.CASCADE, related_name='teams')
    name = models.CharField(max_length=100)
    logo = models.ImageField(upload_to='team_logos/', null=True, blank=True)
    logo_color = models.CharField(max_length=20, default="#000000")
    customization = models.JSONField(default=dict, blank=True)

    @property
    def captain(self):
        return self.user

    def __str__(self):
        return f"{self.name} ({self.user.email})"

class Player(BaseModel):
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='players')
    name = models.CharField(max_length=100)
    role = models.CharField(max_length=50, blank=True)
    is_substitute = models.BooleanField(default=False)

    def __str__(self):
        return self.name

class Tournament(BaseModel):
    TOURNAMENT_TYPES = (
        ('OFFICIAL', 'Official'),
        ('FRIENDLY', 'Friendly'),
    )
    PRIVACY_CHOICES = (
        ('PUBLIC', 'Public'),
        ('PRIVATE', 'Private'),
    )
    STATUS_CHOICES = (
        ('DRAFT', 'Draft'),
        ('ONGOING', 'Ongoing'),
        ('COMPLETED', 'Completed'),
    )

    organizer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='organized_tournaments')
    sport = models.ForeignKey(Sport, on_delete=models.CASCADE, related_name='tournaments')
    name = models.CharField(max_length=150)
    tournament_type = models.CharField(max_length=20, choices=TOURNAMENT_TYPES, default='FRIENDLY')
    privacy = models.CharField(max_length=20, choices=PRIVACY_CHOICES, default='PUBLIC')
    invite_code = models.CharField(max_length=50, blank=True, null=True, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    start_date = models.DateTimeField(null=True, blank=True)
    venue = models.CharField(max_length=200, blank=True)
    
    def __str__(self):
        return f"{self.name} ({self.get_tournament_type_display()})"

class TournamentTeam(BaseModel):
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name='tournament_teams')
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='tournaments_joined')
    is_approved = models.BooleanField(default=True) # For private tournaments

    class Meta:
        unique_together = ('tournament', 'team')

    def __str__(self):
        return f"{self.team.name} in {self.tournament.name}"

class Match(BaseModel):
    MATCH_STATUS = (
        ('SCHEDULED', 'Scheduled'),
        ('ONGOING', 'Ongoing'),
        ('COMPLETED', 'Completed'),
    )
    
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name='matches')
    team1 = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='matches_as_team1', null=True, blank=True)
    team2 = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='matches_as_team2', null=True, blank=True)
    winner = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='matches_won', null=True, blank=True)
    
    round_name = models.CharField(max_length=50) # e.g., 'Quarter Final', 'Round 1'
    match_order = models.IntegerField(default=1) # To sort matches in a bracket
    next_match = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='previous_matches')
    
    score_team1 = models.CharField(max_length=50, blank=True)
    score_team2 = models.CharField(max_length=50, blank=True)
    status = models.CharField(max_length=20, choices=MATCH_STATUS, default='SCHEDULED')
    match_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        t1 = self.team1.name if self.team1 else "TBD"
        t2 = self.team2.name if self.team2 else "TBD"
        return f"{t1} vs {t2} - {self.tournament.name} ({self.round_name})"
