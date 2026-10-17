from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TurfViewSet, CourtViewSet, BlockedPeriodViewSet, PriceRuleViewSet

router = DefaultRouter()
router.register(r'turfs', TurfViewSet, basename='turf')
router.register(r'courts', CourtViewSet, basename='court')
router.register(r'blocked-periods', BlockedPeriodViewSet, basename='blocked-period')
router.register(r'price-rules', PriceRuleViewSet, basename='price-rule')

urlpatterns = [
    path('', include(router.urls)),
]
