import threading
from django.test import TransactionTestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db import connection
from turfs.models import Turf, Court
from sports.models import Sport
from bookings.models import Booking
from bookings.services import BookingService

User = get_user_model()

class BookingConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(email='user1@example.com', username='user1', password='pw')
        self.user2 = User.objects.create_user(email='user2@example.com', username='user2', password='pw')
        self.sport = Sport.objects.create(name='Football', slug='football')
        self.turf = Turf.objects.create(name='Main Turf', slug='main-turf', owner=self.user1, city='City')
        self.court = Court.objects.create(turf=self.turf, name='Court A')

    def test_concurrent_booking(self):
        start_at = timezone.now()
        end_at = start_at + timezone.timedelta(hours=1)

        errors = []
        bookings = []

        def book(user):
            try:
                # Setup a fresh connection for the thread
                connection.connect()
                b = BookingService.create_hold(
                    user=user,
                    court_id=self.court.id,
                    sport_id=self.sport.id,
                    start_at=start_at,
                    end_at=end_at
                )
                bookings.append(b)
            except Exception as e:
                errors.append(e)
            finally:
                connection.close()

        t1 = threading.Thread(target=book, args=(self.user1,))
        t2 = threading.Thread(target=book, args=(self.user2,))

        t1.start()
        t2.start()

        t1.join()
        t2.join()

        # Due to select_for_update row locking, one transaction wins and inserts, 
        # while the other waits and then sees the newly inserted overlapping row.
        self.assertEqual(len(bookings), 1)
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], ValueError)
        self.assertEqual(str(errors[0]), "The selected slot is already booked or held.")
