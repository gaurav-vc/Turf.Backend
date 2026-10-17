from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import LiveScoreViewSet

router = DefaultRouter()
router.register(r'matches', LiveScoreViewSet, basename='livescore')

urlpatterns = [
    path('', include(router.urls)),
]
