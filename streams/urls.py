from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import LiveStreamViewSet

router = DefaultRouter()
router.register(r'live', LiveStreamViewSet, basename='live_streams')

urlpatterns = [
    path('', include(router.urls)),
]
