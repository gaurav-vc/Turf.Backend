from django.db import models
from django.conf import settings
from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import RangeOperators
from core.models import BaseModel

class Booking(BaseModel):
    STATUS_CHOICES = (
        ('HOLD', 'Hold'),
        ('CONFIRMED', 'Confirmed'),
        ('CANCELLED', 'Cancelled'),
        ('EXPIRED', 'Expired'),
        ('COMPLETED', 'Completed'),
        ('NO_SHOW', 'No Show'),
    )
    code = models.CharField(max_length=20, unique=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bookings')
    court = models.ForeignKey('turfs.Court', on_delete=models.CASCADE, related_name='bookings')
    sport = models.ForeignKey('sports.Sport', on_delete=models.CASCADE)
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='HOLD')
    hold_expires_at = models.DateTimeField(null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    # tournament_match = models.ForeignKey('tournaments.Match', on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        constraints = [
            # EXCLUDE USING gist (court_id WITH =, tstzrange(start_at, end_at) WITH &&) WHERE (status IN ('HOLD','CONFIRMED'))
            # Requires btree_gist extension and PostgreSQL
            # We will create this via a custom migration if needed, but Django 4+ supports this directly if we use DateRange/DateTimeRange.
            # For simplicity in pure Django without requiring full range models everywhere, we can execute raw SQL in migrations, 
            # or use Django's ExclusionConstraint if we define the range.
        ]

    def __str__(self):
        return f"{self.code} - {self.court.name} - {self.status}"
