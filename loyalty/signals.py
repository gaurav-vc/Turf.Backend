from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .models import Wallet, Transaction
from bookings.models import Booking
import decimal

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_wallet(sender, instance, created, **kwargs):
    if created:
        Wallet.objects.create(user=instance, balance=50.00) # Give 50 free TurfCoins on signup!
        
@receiver(post_save, sender=Booking)
def award_turf_coins(sender, instance, created, **kwargs):
    # Only award coins when booking is confirmed
    # In a real app, you might want to track if coins were already awarded for this booking
    if instance.status == 'CONFIRMED' and instance.amount > 0:
        wallet, _ = Wallet.objects.get_or_create(user=instance.user)
        
        # Check if already awarded (simple check using booking reference)
        if not Transaction.objects.filter(wallet=wallet, booking_reference=instance.code).exists():
            # Award logic: Every ₹100 spent = 1 TurfCoin
            coins_earned = decimal.Decimal(instance.amount) / decimal.Decimal('100.0')
            coins_earned = round(coins_earned, 2)
            
            if coins_earned > 0:
                wallet.balance += coins_earned
                wallet.save()
                
                Transaction.objects.create(
                    wallet=wallet,
                    amount=coins_earned,
                    transaction_type='CREDIT',
                    reason=f"Earned from Booking #{instance.code}",
                    booking_reference=instance.code
                )
