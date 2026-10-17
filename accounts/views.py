from rest_framework import viewsets, mixins, generics, status
from django.contrib.auth import get_user_model
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from django.core.mail import send_mail
from django.utils import timezone
import random
from datetime import timedelta
from .models import OTPVerification
from .serializers import UserSerializer, UserUpdateSerializer, RegisterSerializer, SendOTPSerializer, ForgotPasswordSendOTPSerializer, ResetPasswordSerializer

User = get_user_model()

class SendOTPView(generics.GenericAPIView):
    permission_classes = (AllowAny,)
    serializer_class = SendOTPSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        
        # Generate OTP
        otp = str(random.randint(100000, 999999))
        
        # Save OTP to database
        OTPVerification.objects.update_or_create(
            email=email,
            defaults={
                'otp': otp,
                'is_verified': False,
                'expires_at': timezone.now() + timedelta(minutes=10)
            }
        )
        
        # Send professional HTML email
        subject = 'Verify Your Email - Welcome to TurfArena!'
        message = f'Your verification code is: {otp}. It expires in 10 minutes.'
        html_message = f"""
        <html>
            <body style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; background-color: #f4f4f5; padding: 40px 20px; margin: 0;">
                <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; padding: 40px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
                    <div style="text-align: center; margin-bottom: 30px;">
                        <h1 style="color: #10b981; margin: 0; font-size: 32px; font-weight: 900; letter-spacing: -1px;">TURF<span style="color: #18181b;">ARENA</span></h1>
                    </div>
                    <h2 style="color: #18181b; font-size: 24px; font-weight: 700; margin-bottom: 20px;">Verify your email address</h2>
                    <p style="color: #52525b; font-size: 16px; line-height: 1.6; margin-bottom: 30px;">
                        Thank you for registering with TurfArena! To complete your sign-up process and secure your account, please use the verification code below.
                    </p>
                    <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 24px; text-align: center; margin-bottom: 30px;">
                        <span style="font-family: monospace; font-size: 36px; font-weight: 800; color: #10b981; letter-spacing: 8px;">{otp}</span>
                    </div>
                    <p style="color: #71717a; font-size: 14px; line-height: 1.6; margin-bottom: 30px;">
                        This code will expire in <strong>10 minutes</strong>. For security reasons, please do not share this code with anyone. If you did not request this, you can safely ignore this email.
                    </p>
                    <hr style="border: none; border-top: 1px solid #e2e8f0; margin-bottom: 20px;">
                    <p style="color: #a1a1aa; font-size: 12px; text-align: center; margin: 0; line-height: 1.5;">
                        &copy; 2026 TurfArena. All rights reserved.<br>
                        Elevating your game, one turf at a time.
                    </p>
                </div>
            </body>
        </html>
        """
        
        send_mail(
            subject=subject,
            message=message,
            from_email=None,
            recipient_list=[email],
            fail_silently=False,
            html_message=html_message
        )
        
        return Response({"message": "OTP sent successfully."}, status=status.HTTP_200_OK)

from django.conf import settings

class ForgotPasswordSendOTPView(generics.GenericAPIView):
    permission_classes = (AllowAny,)
    serializer_class = ForgotPasswordSendOTPSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        
        # Generate OTP
        otp = str(random.randint(100000, 999999))
        
        # Save OTP to database
        OTPVerification.objects.update_or_create(
            email=email,
            defaults={
                'otp': otp,
                'is_verified': False,
                'expires_at': timezone.now() + timedelta(minutes=10)
            }
        )
        
        try:
            subject = 'Password Reset - TurfArena'
            message = f'Your password reset code is: {otp}. It expires in 10 minutes.'
            send_mail(
                subject,
                message,
                settings.EMAIL_HOST_USER,
                [email],
                fail_silently=True,
            )
        except Exception as e:
            print(f"Failed to send reset email: {str(e)}")

        return Response({'message': 'Password reset OTP sent successfully'}, status=status.HTTP_200_OK)

class ResetPasswordView(generics.GenericAPIView):
    permission_classes = (AllowAny,)
    serializer_class = ResetPasswordSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'message': 'Password reset successfully'}, status=status.HTTP_200_OK)

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = RegisterSerializer

from rest_framework.permissions import IsAdminUser

class AdminCreateUserView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (IsAdminUser,)
    
    # We can reuse RegisterSerializer but remove the OTP requirement in a custom way,
    # or just create the user manually.
    def post(self, request, *args, **kwargs):
        email = request.data.get('email')
        password = request.data.get('password')
        full_name = request.data.get('full_name', '')
        phone = request.data.get('phone', '')
        
        if not email or not password:
            return Response({"error": "Email and password are required."}, status=status.HTTP_400_BAD_REQUEST)
            
        if User.objects.filter(email=email).exists():
            return Response({"error": "User with this email already exists."}, status=status.HTTP_400_BAD_REQUEST)
            
        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            full_name=full_name,
            phone=phone
        )
        
        # Send Welcome Email
        try:
            from django.core.mail import send_mail
            from django.conf import settings
            
            subject = 'Welcome to Turf Management System - Manager Account'
            message = f'''Hello {full_name},
            
Your Manager account has been successfully created by the Admin.

Here are your login credentials:
Login ID (Email): {email}
Temporary Password: {password}

Please log in and change your password as soon as possible.

Best regards,
Turf Admin Team
'''
            send_mail(
                subject,
                message,
                settings.EMAIL_HOST_USER,
                [email],
                fail_silently=True,
            )
        except Exception as e:
            print(f"Failed to send manager creation email: {str(e)}")

        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)

from rest_framework.pagination import PageNumberPagination
from rest_framework.filters import SearchFilter

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

from django_filters.rest_framework import DjangoFilterBackend

class UserViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.UpdateModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    queryset = User.objects.all().order_by('-date_joined')
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['user_type']
    search_fields = ['email', 'full_name', 'phone']

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        
        # Only paginate if 'paginate=true' is passed
        if request.query_params.get('paginate') == 'true':
            self.pagination_class = StandardResultsSetPagination
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)
                
        # Otherwise return flat list for backward compatibility
        self.pagination_class = None
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        return UserSerializer

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

from .models import Notification
from .serializers import NotificationSerializer

class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        self.get_queryset().update(is_read=True)
        return Response({'status': 'ok'})
