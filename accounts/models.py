from django.db import models
from django.contrib.auth.models import AbstractUser
from core.models import BaseModel

class User(AbstractUser, BaseModel):
    USER_TYPE_CHOICES = (
        ('ADMIN', 'Admin'),
        ('MANAGER', 'Manager'),
        ('PLAYER', 'Player'),
    )
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    full_name = models.CharField(max_length=255, blank=True)
    avatar = models.URLField(blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES, default='PLAYER')

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email

class OTPVerification(BaseModel):
    email = models.EmailField(unique=True)
    otp = models.CharField(max_length=6)
    is_verified = models.BooleanField(default=False)
    expires_at = models.DateTimeField()

    def __str__(self):
        return f"{self.email} - {self.otp}"

class PlayerProfile(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    city = models.CharField(max_length=100, blank=True)
    dob = models.DateField(null=True, blank=True)
    preferences = models.JSONField(default=dict, blank=True)

class PlayerSportRole(BaseModel):
    player = models.ForeignKey(PlayerProfile, on_delete=models.CASCADE, related_name='sport_roles')
    sport = models.ForeignKey('sports.Sport', on_delete=models.CASCADE)
    role = models.CharField(max_length=50)
    is_primary = models.BooleanField(default=False)

class TurfManagerMembership(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='turf_memberships')
    turf = models.ForeignKey('turfs.Turf', on_delete=models.CASCADE, related_name='managers')

class Notification(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    type = models.CharField(max_length=50, default='SYSTEM')
    link = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - {self.title}"
