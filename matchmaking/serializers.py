from rest_framework import serializers
from .models import MatchmakingLobby, LobbyRequest
from accounts.serializers import UserSerializer
from turfs.serializers import TurfSerializer
from sports.serializers import SportSerializer

class MatchmakingLobbySerializer(serializers.ModelSerializer):
    host_details = UserSerializer(source='host', read_only=True)
    sport_details = SportSerializer(source='sport', read_only=True)
    turf_details = TurfSerializer(source='turf', read_only=True)
    current_players = serializers.SerializerMethodField()
    
    class Meta:
        model = MatchmakingLobby
        fields = '__all__'
        read_only_fields = ('host', 'is_active')

    def get_current_players(self, obj):
        # Count accepted requests
        return obj.requests.filter(status='ACCEPTED').count() + 1 # +1 for host

class LobbyRequestSerializer(serializers.ModelSerializer):
    player_details = UserSerializer(source='player', read_only=True)
    lobby_details = MatchmakingLobbySerializer(source='lobby', read_only=True)

    class Meta:
        model = LobbyRequest
        fields = '__all__'
        read_only_fields = ('player',)
