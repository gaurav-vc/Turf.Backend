from rest_framework import serializers
from .models import Sport, RuleSet, Team, Player

class RuleSetSerializer(serializers.ModelSerializer):
    class Meta:
        model = RuleSet
        fields = '__all__'

class SportSerializer(serializers.ModelSerializer):
    rulesets = RuleSetSerializer(many=True, read_only=True)
    slug = serializers.SlugField(required=False)
    scoring_engine = serializers.CharField(required=False, default='standard')
    
    class Meta:
        model = Sport
        fields = '__all__'

    def create(self, validated_data):
        if not validated_data.get('slug'):
            from django.utils.text import slugify
            validated_data['slug'] = slugify(validated_data.get('name', 'sport'))
        if not validated_data.get('scoring_engine'):
            validated_data['scoring_engine'] = 'standard'
        return super().create(validated_data)

class PlayerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Player
        fields = ['id', 'name', 'role', 'is_substitute']

class TeamSerializer(serializers.ModelSerializer):
    players = PlayerSerializer(many=True, read_only=True)
    sport_name = serializers.CharField(source='sport.name', read_only=True)
    is_owner = serializers.SerializerMethodField()

    class Meta:
        model = Team
        fields = ['id', 'sport', 'sport_name', 'name', 'logo', 'logo_color', 'customization', 'players', 'is_owner']
        read_only_fields = ['id', 'is_owner']

    def get_is_owner(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.user_id == request.user.id
        return False

    def _extract_players(self):
        players_data = []
        if 'players' in self.initial_data:
            players_raw = self.initial_data.get('players')
            if hasattr(self.initial_data, 'getlist'):
                raw_list = self.initial_data.getlist('players')
                if raw_list and isinstance(raw_list[0], str) and raw_list[0].startswith('['):
                    players_raw = raw_list[0]
            import json
            if isinstance(players_raw, str):
                try:
                    players_data = json.loads(players_raw)
                except Exception:
                    pass
            elif isinstance(players_raw, list):
                if len(players_raw) > 0 and isinstance(players_raw[0], str):
                    try:
                        players_data = json.loads(players_raw[0])
                    except Exception:
                        pass
                else:
                    players_data = players_raw
        return players_data

    def create(self, validated_data):
        players_data = self._extract_players()
        user = self.context['request'].user
        team = Team.objects.create(user=user, **validated_data)
        
        for player_data in players_data:
            # exclude id if present for new players
            player_data.pop('id', None)
            Player.objects.create(team=team, **player_data)
            
        return team

    def update(self, instance, validated_data):
        players_data = self._extract_players()
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        if 'players' in self.initial_data:
            instance.players.all().delete()
            for player_data in players_data:
                player_data.pop('id', None)
                Player.objects.create(team=instance, **player_data)
                
        return instance

from .models import Tournament, TournamentTeam, Match

class TournamentTeamSerializer(serializers.ModelSerializer):
    team_name = serializers.CharField(source='team.name', read_only=True)
    team_logo = serializers.CharField(source='team.logo_color', read_only=True)

    class Meta:
        model = TournamentTeam
        fields = ['id', 'tournament', 'team', 'team_name', 'team_logo', 'is_approved']

class MatchSerializer(serializers.ModelSerializer):
    team1_name = serializers.CharField(source='team1.name', read_only=True)
    team2_name = serializers.CharField(source='team2.name', read_only=True)
    winner_name = serializers.CharField(source='winner.name', read_only=True)
    sport_scoring_engine = serializers.CharField(source='tournament.sport.scoring_engine', read_only=True)

    class Meta:
        model = Match
        fields = '__all__'

class TournamentSerializer(serializers.ModelSerializer):
    organizer_name = serializers.CharField(source='organizer.name', read_only=True)
    sport_name = serializers.CharField(source='sport.name', read_only=True)
    teams = TournamentTeamSerializer(source='tournament_teams', many=True, read_only=True)
    matches = MatchSerializer(many=True, read_only=True)

    class Meta:
        model = Tournament
        fields = ['id', 'name', 'sport', 'sport_name', 'organizer', 'organizer_name', 'tournament_type', 'privacy', 'invite_code', 'status', 'start_date', 'venue', 'teams', 'matches']
        read_only_fields = ['id', 'organizer', 'invite_code']

    def create(self, validated_data):
        validated_data['organizer'] = self.context['request'].user
        import uuid
        if validated_data.get('privacy') == 'PRIVATE':
            validated_data['invite_code'] = str(uuid.uuid4())[:8].upper()
        return super().create(validated_data)
