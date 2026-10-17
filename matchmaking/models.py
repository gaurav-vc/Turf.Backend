from django.db import models
from django.conf import settings
from core.models import BaseModel

class MatchmakingLobby(BaseModel):
    SKILL_LEVELS = (
        ('BEGINNER', 'Beginner'),
        ('INTERMEDIATE', 'Intermediate'),
        ('ADVANCED', 'Advanced'),
        ('ALL', 'All Levels'),
    )
    
    host = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='hosted_lobbies')
    sport = models.ForeignKey('sports.Sport', on_delete=models.CASCADE, related_name='matchmaking_lobbies')
    title = models.CharField(max_length=200)
    turf = models.ForeignKey('turfs.Turf', on_delete=models.SET_NULL, null=True, blank=True, related_name='lobbies')
    date_time = models.DateTimeField()
    players_needed = models.IntegerField(default=1)
    skill_level = models.CharField(max_length=20, choices=SKILL_LEVELS, default='ALL')
    cost_per_person = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.title} by {self.host.email}"

class LobbyRequest(BaseModel):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('ACCEPTED', 'Accepted'),
        ('REJECTED', 'Rejected'),
    )
    lobby = models.ForeignKey(MatchmakingLobby, on_delete=models.CASCADE, related_name='requests')
    player = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='lobby_requests')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    message = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ('lobby', 'player')

    def __str__(self):
        return f"{self.player.email} -> {self.lobby.title} ({self.status})"
