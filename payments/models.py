from django.db import models
from core.models import BaseModel

class Payment(BaseModel):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
        ('REFUNDED', 'Refunded'),
    )
    booking = models.ForeignKey('bookings.Booking', on_delete=models.CASCADE, related_name='payments', null=True, blank=True)
    # entry = models.ForeignKey('tournaments.TournamentTeam', ...) # for later
    provider = models.CharField(max_length=50) # 'razorpay', 'stripe'
    provider_payment_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default='INR')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    raw_data = models.JSONField(default=dict, blank=True)

class Refund(BaseModel):
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='refunds')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20)

class Coupon(BaseModel):
    code = models.CharField(max_length=50, unique=True)
    rules = models.JSONField(default=dict, blank=True)

class Payout(BaseModel):
    turf = models.ForeignKey('turfs.Turf', on_delete=models.CASCADE, related_name='payouts')
    period_start = models.DateField()
    period_end = models.DateField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=50)
