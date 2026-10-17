from django.urls import path
from .views import ManagerDashboardAnalyticsView, GenerateDemoAnalyticsView

urlpatterns = [
    path('manager-dashboard/', ManagerDashboardAnalyticsView.as_view(), name='manager-analytics'),
    path('generate-demo-data/', GenerateDemoAnalyticsView.as_view(), name='generate-demo-data'),
]
