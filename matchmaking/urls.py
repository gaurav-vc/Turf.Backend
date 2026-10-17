from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MatchmakingLobbyViewSet, LobbyRequestViewSet

router = DefaultRouter()
router.register(r'lobbies', MatchmakingLobbyViewSet, basename='lobby')
router.register(r'requests', LobbyRequestViewSet, basename='lobby-request')

urlpatterns = [
    path('', include(router.urls)),
]
