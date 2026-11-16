from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AuctionViewSet, AuctionTeamViewSet, AuctionPlayerViewSet, BidViewSet
from .views_v24 import (
    Phase2AuctionConsoleViewSet,
    AuctionCategoryViewSet,
    BidSlabViewSet,
    SquadRuleViewSet,
    CustomFieldDefinitionViewSet,
    AuctionSponsorItemViewSet,
    AuctionMediaItemViewSet,
    PublicSpectatorStateView,
    PublicPlayerRegistrationView,
)

router = DefaultRouter()
# Preserved legacy routes (100% backward-compatible)
router.register(r'auctions', AuctionViewSet, basename='auctions')
router.register(r'teams', AuctionTeamViewSet, basename='auction_teams')
router.register(r'players', AuctionPlayerViewSet, basename='auction_players')
router.register(r'bids', BidViewSet, basename='bids')

# Phase 2 Modular Routes (Additive & Isolated)
router.register(r'console', Phase2AuctionConsoleViewSet, basename='auction_console')
router.register(r'categories', AuctionCategoryViewSet, basename='auction_categories')
router.register(r'slabs', BidSlabViewSet, basename='auction_slabs')
router.register(r'squad-rules', SquadRuleViewSet, basename='auction_squad_rules')
router.register(r'custom-fields', CustomFieldDefinitionViewSet, basename='auction_custom_fields')
router.register(r'sponsors', AuctionSponsorItemViewSet, basename='auction_sponsors')
router.register(r'media', AuctionMediaItemViewSet, basename='auction_media')

urlpatterns = [
    # Direct Action Routes for guaranteed matching across all DRF configurations
    path('console/<str:pk>/sync_drive_photos/', Phase2AuctionConsoleViewSet.as_view({'post': 'sync_drive_photos', 'get': 'sync_drive_photos'}), name='auction_console_sync_drive_photos'),
    path('', include(router.urls)),
    # Public Spectator & Registration Endpoints (No Auth)
    path('public/viewer/<str:token>/', PublicSpectatorStateView.as_view(), name='public_spectator_state'),
    path('public/register/<str:token>/', PublicPlayerRegistrationView.as_view(), name='public_player_registration'),
]
