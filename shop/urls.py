from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProductViewSet, ShopOrderViewSet

router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='products')
router.register(r'orders', ShopOrderViewSet, basename='shop_orders')

urlpatterns = [
    path('', include(router.urls)),
]
