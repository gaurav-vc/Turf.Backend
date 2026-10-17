from django.db import transaction
from django.utils import timezone
from .models import Booking
from turfs.models import Court
import random
import string

class BookingService:
    @staticmethod
    def create_hold(user, court_id, sport_id, start_at, end_at):
        """
        Creates a HOLD booking for a given court and time range.
        Uses select_for_update to prevent concurrent double bookings.
        """
        with transaction.atomic():
            # Lock the court row to serialize concurrent booking attempts on the same court
            court = Court.objects.select_for_update().get(id=court_id)

            # Check for overlapping bookings that are HOLD or CONFIRMED
            overlapping = Booking.objects.filter(
                court=court,
                status__in=['HOLD', 'CONFIRMED'],
                start_at__lt=end_at,
                end_at__gt=start_at
            ).exists()

            if overlapping:
                raise ValueError("The selected slot is already booked or held.")

            # Calculate hold expiry (8 minutes from now)
            hold_expires_at = timezone.now() + timezone.timedelta(minutes=8)

            booking = Booking.objects.create(
                code=BookingService._generate_code(),
                user=user,
                court=court,
                sport_id=sport_id,
                start_at=start_at,
                end_at=end_at,
                status='HOLD',
                hold_expires_at=hold_expires_at
            )
            return booking

    @staticmethod
    def _generate_code():
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
