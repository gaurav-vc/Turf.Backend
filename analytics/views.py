from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from django.db.models import Sum, Count, Max, F
from django.utils import timezone
from datetime import timedelta
from bookings.models import Booking
from accounts.models import User

class ManagerDashboardAnalyticsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        
        # Filter bookings for turfs owned by this manager
        manager_bookings = Booking.objects.filter(court__turf__owner=user)
        
        # Calculate Total Revenue
        total_revenue = manager_bookings.filter(status__in=['CONFIRMED', 'COMPLETED']).aggregate(Sum('amount'))['amount__sum'] or 0

        # Calculate Total Bookings
        total_bookings = manager_bookings.count()
        
        # Calculate Upcoming Bookings (Active pipeline)
        upcoming_bookings = manager_bookings.filter(
            status='CONFIRMED', 
            start_at__gte=timezone.now()
        ).count()
        
        # Calculate Unique Customers
        unique_customers = manager_bookings.values('user').distinct().count()

        # Customer Lifetime Value (CLV) Calculation (Top 5 Customers)
        clv_data = manager_bookings.filter(status__in=['CONFIRMED', 'COMPLETED']).values(
            'user__email', 'user__first_name', 'user__last_name'
        ).annotate(
            total_spent=Sum('amount'),
            booking_count=Count('id'),
            last_booking=Max('start_at')
        ).order_by('-total_spent')[:5]

        # Churning Customers (Booked in past, but not in last 21 days)
        three_weeks_ago = timezone.now() - timedelta(days=21)
        churning_customers = manager_bookings.filter(
            status__in=['CONFIRMED', 'COMPLETED']
        ).values(
            'user__email', 'user__first_name'
        ).annotate(
            last_booking=Max('start_at')
        ).filter(
            last_booking__lt=three_weeks_ago
        ).order_by('-last_booking')[:10]

        # Revenue Trend (Last 7 Days)
        seven_days_ago = timezone.now() - timedelta(days=7)
        daily_revenue_data = manager_bookings.filter(
            status__in=['CONFIRMED', 'COMPLETED'],
            start_at__gte=seven_days_ago
        ).values('start_at__date').annotate(
            revenue=Sum('amount')
        ).order_by('start_at__date')
        
        # Format for charts
        revenue_trend = []
        for d in range(7, -1, -1):
            date_obj = (timezone.now() - timedelta(days=d)).date()
            revenue_for_day = next((item['revenue'] for item in daily_revenue_data if item['start_at__date'] == date_obj), 0)
            revenue_trend.append({
                'date': date_obj.strftime('%b %d'),
                'revenue': float(revenue_for_day or 0)
            })

        return Response({
            'total_revenue': float(total_revenue),
            'total_bookings': total_bookings,
            'upcoming_bookings': upcoming_bookings,
            'unique_customers': unique_customers,
            'top_customers_clv': list(clv_data),
            'churning_customers': list(churning_customers),
            'revenue_trend': revenue_trend
        })

class GenerateDemoAnalyticsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        import random
        from datetime import timedelta
        from django.utils import timezone
        from turfs.models import Turf, Court
        from accounts.models import User
        from bookings.models import Booking

        # Ensure manager has a turf
        turf, _ = Turf.objects.get_or_create(
            owner=request.user,
            defaults={
                'name': 'Demo Ace Arena',
                'description': 'A demo turf for analytics',
                'address': '123 Analytics St',
                'city': 'Demo City'
            }
        )
        court, _ = Court.objects.get_or_create(
            turf=turf,
            defaults={'name': 'Court 1 - 5v5', 'court_type': '5v5'}
        )

        # Create demo customers
        customers = []
        for i in range(5):
            u, _ = User.objects.get_or_create(
                email=f"demo_customer_{i}@example.com",
                defaults={'username': f"democust{i}", 'first_name': f"DemoUser", 'last_name': str(i)}
            )
            customers.append(u)

        # Create some churning customers (last booking 30 days ago)
        churn_date = timezone.now() - timedelta(days=30)
        for u in customers[:2]:
            Booking.objects.create(
                user=u,
                court=court,
                start_at=churn_date,
                end_at=churn_date + timedelta(hours=1),
                amount=1500.00,
                status='COMPLETED'
            )

        # Create some high CLV active customers
        active_date = timezone.now() - timedelta(days=2)
        for u in customers[2:]:
            for j in range(random.randint(3, 6)):
                Booking.objects.create(
                    user=u,
                    court=court,
                    start_at=active_date - timedelta(days=j*2),
                    end_at=active_date - timedelta(days=j*2) + timedelta(hours=1),
                    amount=1200.00,
                    status='COMPLETED'
                )

        return Response({'status': 'Demo data generated successfully!'})
