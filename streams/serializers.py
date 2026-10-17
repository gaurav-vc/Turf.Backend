from rest_framework import serializers
from .models import LiveStream

class LiveStreamSerializer(serializers.ModelSerializer):
    organizer_name = serializers.SerializerMethodField()
    organizer_email = serializers.EmailField(source='organizer.email', read_only=True)
    organizer_id = serializers.IntegerField(source='organizer.id', read_only=True)
    
    class Meta:
        model = LiveStream
        fields = '__all__'
        read_only_fields = ['organizer', 'viewer_count']

    def get_organizer_name(self, obj):
        if not obj.organizer:
            return 'Umpire'
        return getattr(obj.organizer, 'full_name', '') or obj.organizer.first_name or obj.organizer.username or (obj.organizer.email.split('@')[0] if obj.organizer.email else 'Umpire')
