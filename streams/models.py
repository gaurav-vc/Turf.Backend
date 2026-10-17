from django.db import models
from core.models import BaseModel
from accounts.models import User

class LiveStream(BaseModel):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    stream_url = models.URLField()
    organizer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='streams')
    is_live = models.BooleanField(default=True)
    viewer_count = models.PositiveIntegerField(default=0)
    
    def __str__(self):
        return f"{self.title} ({'LIVE' if self.is_live else 'ENDED'})"
