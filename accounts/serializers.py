from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import OTPVerification

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'full_name', 'phone', 'avatar', 'user_type', 'is_active', 'date_joined', 'is_superuser']
        read_only_fields = ['id', 'date_joined', 'email', 'is_superuser']

class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['full_name', 'phone', 'avatar', 'user_type', 'is_active']

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    otp = serializers.CharField(write_only=True, max_length=6, required=True)
    
    class Meta:
        model = User
        fields = ['email', 'password', 'full_name', 'phone', 'otp']

    def validate(self, attrs):
        email = attrs.get('email')
        otp = attrs.get('otp')

        try:
            otp_record = OTPVerification.objects.get(email=email, otp=otp, is_verified=False)
            if otp_record.expires_at < timezone.now():
                raise serializers.ValidationError({"otp": "OTP has expired."})
            otp_record.is_verified = True
            otp_record.save()
        except OTPVerification.DoesNotExist:
            raise serializers.ValidationError({"otp": "Invalid OTP."})

        return attrs

    def create(self, validated_data):
        # Remove otp from validated_data since it's not a User model field
        validated_data.pop('otp', None)
        user = User.objects.create_user(
            username=validated_data['email'], # AbstractUser requires username
            email=validated_data['email'],
            password=validated_data['password'],
            full_name=validated_data.get('full_name', ''),
            phone=validated_data.get('phone', '')
        )
        return user

class SendOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

class ForgotPasswordSendOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("No account found with this email.")
        return value

class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)
    new_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get('email')
        otp = attrs.get('otp')

        try:
            otp_record = OTPVerification.objects.get(email=email, otp=otp, is_verified=False)
            if otp_record.expires_at < timezone.now():
                raise serializers.ValidationError({"otp": "OTP has expired."})
            attrs['otp_record'] = otp_record
        except OTPVerification.DoesNotExist:
            raise serializers.ValidationError({"otp": "Invalid OTP."})

        return attrs

    def save(self):
        email = self.validated_data['email']
        new_password = self.validated_data['new_password']
        otp_record = self.validated_data['otp_record']

        user = User.objects.get(email=email)
        user.set_password(new_password)
        user.save()

        otp_record.is_verified = True
        otp_record.save()
        return user

from .models import Notification

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'title', 'message', 'is_read', 'type', 'link', 'created_at']
        read_only_fields = ['id', 'created_at']
