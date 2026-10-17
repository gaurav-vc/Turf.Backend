from django.db import models
from core.models import BaseModel

class LiveScore(BaseModel):
    match = models.OneToOneField('sports.Match', on_delete=models.CASCADE, related_name='live_score')
    team1_score = models.IntegerField(default=0)
    team2_score = models.IntegerField(default=0)
    current_inning = models.IntegerField(default=1)
    event_log = models.JSONField(default=list, blank=True)
    is_live = models.BooleanField(default=False)

    def __str__(self):
        return f"Live Score for {self.match}"
