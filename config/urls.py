from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path('admin/', admin.site.urls),
    # API docs
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    # Apps
    path('api/v1/accounts/', include('accounts.urls')),
    path('api/v1/turfs-app/', include('turfs.urls')),
    path('api/v1/bookings/', include('bookings.urls')),
    path('api/v1/sports/', include('sports.urls')),
    path('api/v1/matchmaking/', include('matchmaking.urls')),
    path('api/v1/analytics/', include('analytics.urls')),
    path('api/v1/livescore/', include('livescore.urls')),
    path('api/v1/loyalty/', include('loyalty.urls')),
    path('api/v1/core/', include('core.urls')),
    path('api/v1/payments/', include('payments.urls')),
    path('api/v1/shop/', include('shop.urls')),
    path('api/v1/streams/', include('streams.urls')),
    path('api/v1/auction/', include('auction.urls')),
    path('api/v1/clubs/', include('clubs.urls')),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]

from django.conf import settings
from django.conf.urls.static import static

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
