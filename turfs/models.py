from django.db import models
from core.models import BaseModel
from django.conf import settings

class Turf(BaseModel):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='owned_turfs')
    city = models.CharField(max_length=100)
    address = models.TextField()
    location = models.CharField(max_length=255, blank=True) # Could use PostGIS PointField later
    timezone = models.CharField(max_length=50, default='UTC')
    description = models.TextField(blank=True)
    rating_avg = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    status = models.CharField(max_length=20, default='ACTIVE')

    def __str__(self):
        return self.name

class TurfImage(BaseModel):
    turf = models.ForeignKey(Turf, on_delete=models.CASCADE, related_name='images')
    image_url = models.URLField()
    is_primary = models.BooleanField(default=False)

class Amenity(BaseModel):
    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=100, blank=True)

class TurfAmenity(BaseModel):
    turf = models.ForeignKey(Turf, on_delete=models.CASCADE, related_name='amenities')
    amenity = models.ForeignKey(Amenity, on_delete=models.CASCADE)

class Court(BaseModel):
    turf = models.ForeignKey(Turf, on_delete=models.CASCADE, related_name='courts')
    name = models.CharField(max_length=100)
    surface = models.CharField(max_length=100, blank=True)
    capacity = models.IntegerField(default=10)

    def __str__(self):
        return f"{self.turf.name} - {self.name}"

class CourtSport(BaseModel):
    court = models.ForeignKey(Court, on_delete=models.CASCADE, related_name='supported_sports')
    sport = models.ForeignKey('sports.Sport', on_delete=models.CASCADE)
    price_multiplier = models.DecimalField(max_digits=4, decimal_places=2, default=1.00)

class SlotTemplate(BaseModel):
    court = models.ForeignKey(Court, on_delete=models.CASCADE, related_name='slot_templates')
    weekday = models.IntegerField(help_text="0=Monday, 6=Sunday")
    start_time = models.TimeField()
    end_time = models.TimeField()
    slot_minutes = models.IntegerField(default=60)

class PriceRule(BaseModel):
    court = models.ForeignKey(Court, on_delete=models.CASCADE, related_name='price_rules', null=True, blank=True)
    turf = models.ForeignKey(Turf, on_delete=models.CASCADE, related_name='price_rules', null=True, blank=True)
    sport = models.ForeignKey('sports.Sport', on_delete=models.CASCADE, null=True, blank=True)
    priority = models.IntegerField(default=0)
    conditions = models.JSONField(default=dict, blank=True)
    rule_type = models.CharField(max_length=50) # fixed, multiplier, discount
    value = models.DecimalField(max_digits=10, decimal_places=2)

class BlockedPeriod(BaseModel):
    court = models.ForeignKey(Court, on_delete=models.CASCADE, related_name='blocks')
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    reason = models.CharField(max_length=255)

class CancellationPolicy(BaseModel):
    turf = models.OneToOneField(Turf, on_delete=models.CASCADE, related_name='cancellation_policy')
    rules = models.JSONField(default=dict, blank=True)
