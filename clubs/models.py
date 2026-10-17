import uuid
from django.db import models
from django.conf import settings
from core.models import BaseModel

class Club(BaseModel):
    name = models.CharField(max_length=150)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    logo = models.ImageField(upload_to='club_logos/', null=True, blank=True)
    banner = models.ImageField(upload_to='club_banners/', null=True, blank=True)
    theme_color = models.CharField(max_length=20, default='#10b981')
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='owned_clubs'
    )
    home_turf = models.ForeignKey(
        'turfs.Turf',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='affiliated_clubs'
    )
    sport = models.ForeignKey(
        'sports.Sport',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='clubs'
    )
    privacy = models.CharField(
        max_length=20,
        choices=[('PUBLIC', 'Public'), ('PRIVATE', 'Private'), ('INVITE_ONLY', 'Invite Only')],
        default='PUBLIC'
    )
    invite_code = models.CharField(max_length=20, unique=True, blank=True)
    customization = models.JSONField(default=dict, blank=True)

    def save(self, *args, **kwargs):
        if not self.invite_code:
            self.invite_code = uuid.uuid4().hex[:8].upper()
        if not self.slug:
            from django.utils.text import slugify
            base_slug = slugify(self.name) or 'club'
            slug = base_slug
            counter = 1
            while Club.objects.filter(slug=slug).exclude(id=self.id).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class ClubMember(BaseModel):
    ROLE_CHOICES = (
        ('OWNER', 'Owner'),
        ('CO_OWNER', 'Co-Owner'),
        ('CO_ADMIN', 'Co-Administrator'),
        ('SCORER', 'Official Scorer'),
        ('MEMBER', 'Member'),
    )
    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='club_memberships')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='MEMBER')
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('club', 'user')

    def __str__(self):
        return f"{self.user.email} - {self.club.name} ({self.role})"


class ClubTournament(BaseModel):
    STATUS_CHOICES = (
        ('DRAFT', 'Draft'),
        ('UPCOMING', 'Upcoming'),
        ('ONGOING', 'Ongoing'),
        ('COMPLETED', 'Completed'),
    )
    RECURRENCE_CHOICES = (
        ('NONE', 'Single Event'),
        ('CUSTOM_DATES', 'Arbitrary Custom Dates'),
        ('WEEKLY', 'Weekly Schedule'),
        ('MONTHLY', 'Monthly Schedule'),
    )

    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name='tournaments')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='UPCOMING')
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    venue = models.CharField(max_length=200, blank=True)
    
    # Dynamic Recurrence Configuration
    is_recurring = models.BooleanField(default=False)
    recurrence_type = models.CharField(max_length=30, choices=RECURRENCE_CHOICES, default='NONE')
    recurrence_dates = models.JSONField(default=list, blank=True)
    tournament_rules = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"{self.name} ({self.club.name})"


class ClubMatch(BaseModel):
    STATUS_CHOICES = (
        ('SCHEDULED', 'Scheduled'),
        ('TOSS', 'Toss Pending / In Progress'),
        ('IN_PROGRESS', 'In Progress'),
        ('INNING_BREAK', 'Inning Break'),
        ('COMPLETED', 'Completed'),
        ('ABANDONED', 'Abandoned'),
    )

    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name='matches')
    tournament = models.ForeignKey(ClubTournament, on_delete=models.SET_NULL, null=True, blank=True, related_name='matches')
    team1 = models.ForeignKey('sports.Team', on_delete=models.CASCADE, related_name='club_matches_as_team1')
    team2 = models.ForeignKey('sports.Team', on_delete=models.CASCADE, related_name='club_matches_as_team2')
    turf = models.ForeignKey('turfs.Turf', on_delete=models.SET_NULL, null=True, blank=True, related_name='club_matches')
    court = models.ForeignKey('turfs.Court', on_delete=models.SET_NULL, null=True, blank=True)
    match_date = models.DateTimeField()
    round_name = models.CharField(max_length=100, default='Club Match')

    # Configurable Squad & Wicket Rules (e.g. 7 players -> 6 wickets configurable)
    team1_players_count = models.IntegerField(default=7)
    team2_players_count = models.IntegerField(default=7)
    wickets_allowed = models.IntegerField(default=6)
    last_man_stands = models.BooleanField(default=False)
    is_last_match = models.BooleanField(default=False)
    custom_rules = models.JSONField(default=dict, blank=True)

    # Toss Workflow
    toss_winner = models.ForeignKey('sports.Team', on_delete=models.SET_NULL, null=True, blank=True, related_name='club_tosses_won')
    toss_decision = models.CharField(max_length=10, choices=[('BAT', 'Batting'), ('BOWL', 'Bowling')], blank=True)

    # Result & Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='SCHEDULED')
    winner = models.ForeignKey('sports.Team', on_delete=models.SET_NULL, null=True, blank=True, related_name='club_matches_won')
    result_summary = models.CharField(max_length=255, blank=True)

    def save(self, *args, **kwargs):
        # Auto-calculate default wickets if not explicitly set
        if not self.wickets_allowed and self.team1_players_count:
            self.wickets_allowed = max(1, self.team1_players_count - 1)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.team1.name} vs {self.team2.name} - {self.club.name}"


class LiveMatchTimerState(BaseModel):
    match = models.OneToOneField(ClubMatch, on_delete=models.CASCADE, related_name='timer_state')
    current_inning = models.IntegerField(default=1)
    
    # Dynamic Inning Timer Configuration
    inning_duration_seconds = models.IntegerField(default=780) # Default 13 min = 780s
    reminder_threshold_seconds = models.IntegerField(default=120) # 2 min remaining alert
    
    # Running State
    is_running = models.BooleanField(default=False)
    is_paused = models.BooleanField(default=False)
    
    # Accurate Time Tracking
    elapsed_playing_seconds = models.IntegerField(default=0)
    total_pause_stoppage_seconds = models.IntegerField(default=0) # EXCLUDED from inning duration!
    last_resumed_at = models.DateTimeField(null=True, blank=True)
    
    # Active Break / Pause Event
    active_pause_reason = models.CharField(max_length=100, blank=True)
    active_pause_preset_seconds = models.IntegerField(default=20) # Default 20s for wicket break
    active_pause_started_at = models.DateTimeField(null=True, blank=True)
    
    # Stoppage Log (Audit of all pause breaks)
    pause_events_log = models.JSONField(default=list, blank=True)

    def __str__(self):
        return f"Timer for {self.match} (Inning {self.current_inning})"


class LiveCricketScorecard(BaseModel):
    match = models.OneToOneField(ClubMatch, on_delete=models.CASCADE, related_name='scorecard')
    batting_team = models.ForeignKey('sports.Team', on_delete=models.CASCADE, related_name='club_batting_scorecards', null=True, blank=True)
    bowling_team = models.ForeignKey('sports.Team', on_delete=models.CASCADE, related_name='club_bowling_scorecards', null=True, blank=True)
    
    striker = models.ForeignKey('sports.Player', on_delete=models.SET_NULL, null=True, blank=True, related_name='club_striker_matches')
    non_striker = models.ForeignKey('sports.Player', on_delete=models.SET_NULL, null=True, blank=True, related_name='club_non_striker_matches')
    current_bowler = models.ForeignKey('sports.Player', on_delete=models.SET_NULL, null=True, blank=True, related_name='club_bowler_matches')
    
    total_runs = models.IntegerField(default=0)
    wickets_down = models.IntegerField(default=0)
    balls_bowled = models.IntegerField(default=0) # Legal balls
    extras = models.JSONField(default=dict, blank=True) # {'wides': 0, 'no_balls': 0, 'byes': 0, 'leg_byes': 0, 'penalty': 0}
    
    ball_events = models.JSONField(default=list, blank=True)
    batsmen_stats = models.JSONField(default=dict, blank=True) # {player_id: {name, runs, balls, 4s, 6s, strike_rate, status}}
    bowlers_stats = models.JSONField(default=dict, blank=True) # {player_id: {name, overs, maidens, runs, wickets, economy, average}}
    fall_of_wickets = models.JSONField(default=list, blank=True)
    worm_progression = models.JSONField(default=list, blank=True)
    manhattan_overs = models.JSONField(default=list, blank=True)

    def __str__(self):
        return f"Scorecard: {self.total_runs}/{self.wickets_down} ({self.overs} ov) - {self.match}"

    @property
    def overs(self):
        completed_overs = self.balls_bowled // 6
        extra_balls = self.balls_bowled % 6
        return float(f"{completed_overs}.{extra_balls}")
