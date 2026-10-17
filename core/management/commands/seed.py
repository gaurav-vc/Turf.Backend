from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from sports.models import Sport
from turfs.models import Turf, Court

User = get_user_model()

class Command(BaseCommand):
    help = 'Seeds initial sports, rulesets, and sample turfs'

    def handle(self, *args, **options):
        self.stdout.write('Seeding data...')
        
        # 1. Create Sports
        cricket, _ = Sport.objects.get_or_create(
            name='Cricket', slug='cricket',
            defaults={
                'team_size_min': 11, 'team_size_max': 15,
                'scoring_engine': 'cricket_engine'
            }
        )
        football, _ = Sport.objects.get_or_create(
            name='Football', slug='football',
            defaults={
                'team_size_min': 5, 'team_size_max': 11,
                'scoring_engine': 'goal_engine'
            }
        )
        volleyball, _ = Sport.objects.get_or_create(
            name='Volleyball', slug='volleyball',
            defaults={
                'team_size_min': 6, 'team_size_max': 12,
                'scoring_engine': 'set_engine'
            }
        )

        # 2. Sample User (Turf Manager / Admin)
        admin_user, _ = User.objects.get_or_create(
            email='admin@turfarena.com',
            username='admin',
            defaults={'is_staff': True, 'is_superuser': True, 'user_type': 'ADMIN'}
        )
        if not admin_user.password:
            admin_user.set_password('admin123')
            admin_user.save()

        # 3. Sample Turf
        turf, created = Turf.objects.get_or_create(
            slug='arena-central',
            defaults={
                'name': 'Arena Central',
                'owner': admin_user,
                'city': 'Mumbai',
                'address': '123 Main St, Downtown',
            }
        )

        # Courts
        if created:
            Court.objects.create(turf=turf, name='Cricket Pitch 1', capacity=15)
            Court.objects.create(turf=turf, name='Football 5-a-side A', capacity=10)

        self.stdout.write(self.style.SUCCESS('Successfully seeded sports and sample turfs.'))
