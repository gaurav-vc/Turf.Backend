from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ClubViewSet, ClubTournamentViewSet, ClubMatchViewSet

router = DefaultRouter()
router.register(r'clubs', ClubViewSet, basename='club')
router.register(r'tournaments', ClubTournamentViewSet, basename='club-tournament')
router.register(r'matches', ClubMatchViewSet, basename='club-match')

urlpatterns = [
    path('', include(router.urls)),
]
