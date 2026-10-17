from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'sports', views.SportViewSet)
router.register(r'rulesets', views.RuleSetViewSet)
router.register(r'teams', views.TeamViewSet, basename='team')
router.register(r'tournaments', views.TournamentViewSet, basename='tournament')
router.register(r'tournament-teams', views.TournamentTeamViewSet, basename='tournamentteam')
router.register(r'matches', views.MatchViewSet, basename='match')

urlpatterns = [
    path('', include(router.urls)),
]
