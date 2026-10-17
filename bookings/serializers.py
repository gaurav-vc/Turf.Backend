from rest_framework import serializers
from .models import Booking

class BookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = '__all__'
        read_only_fields = ['code', 'status', 'hold_expires_at']

class CreateHoldSerializer(serializers.Serializer):
    court_id = serializers.UUIDField()
    sport_id = serializers.UUIDField()
    start_at = serializers.DateTimeField()
    end_at = serializers.DateTimeField()
