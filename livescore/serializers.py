from rest_framework import serializers
from .models import LiveScore
from sports.serializers import MatchSerializer

class LiveScoreSerializer(serializers.ModelSerializer):
    match_details = MatchSerializer(source='match', read_only=True)
    
    class Meta:
        model = LiveScore
        fields = '__all__'
