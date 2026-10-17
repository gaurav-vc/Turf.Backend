from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, RegisterView, SendOTPView, AdminCreateUserView, ForgotPasswordSendOTPView, ResetPasswordView, NotificationViewSet

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'notifications', NotificationViewSet, basename='notification')

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('register/send-otp/', SendOTPView.as_view(), name='send_otp'),
    path('admin-create-user/', AdminCreateUserView.as_view(), name='admin_create_user'),
    path('forgot-password/', ForgotPasswordSendOTPView.as_view(), name='forgot_password'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset_password'),
    path('', include(router.urls)),
]
