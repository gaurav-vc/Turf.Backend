from rest_framework import serializers
from .models import (
    Club,
    ClubMember,
    ClubTournament,
    ClubMatch,
    LiveMatchTimerState,
    LiveCricketScorecard
)
from sports.serializers import TeamSerializer, PlayerSerializer
from accounts.models import User

class ClubMemberUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'full_name', 'avatar', 'user_type']

class ClubMemberSerializer(serializers.ModelSerializer):
    user_details = ClubMemberUserSerializer(source='user', read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        source='user',
        write_only=True
    )

    class Meta:
        model = ClubMember
        fields = ['id', 'club', 'user_id', 'user_details', 'role', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']

class ClubTournamentSerializer(serializers.ModelSerializer):
    matches_count = serializers.IntegerField(source='matches.count', read_only=True)

    class Meta:
        model = ClubTournament
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']

class LiveMatchTimerStateSerializer(serializers.ModelSerializer):
    class Meta:
        model = LiveMatchTimerState
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']

class LiveCricketScorecardSerializer(serializers.ModelSerializer):
    striker_name = serializers.CharField(source='striker.name', read_only=True)
    striker_role = serializers.CharField(source='striker.role', read_only=True)
    non_striker_name = serializers.CharField(source='non_striker.name', read_only=True)
    non_striker_role = serializers.CharField(source='non_striker.role', read_only=True)
    current_bowler_name = serializers.CharField(source='current_bowler.name', read_only=True)
    current_bowler_role = serializers.CharField(source='current_bowler.role', read_only=True)
    batting_team_name = serializers.CharField(source='batting_team.name', read_only=True)
    bowling_team_name = serializers.CharField(source='bowling_team.name', read_only=True)
    overs = serializers.ReadOnlyField()

    class Meta:
        model = LiveCricketScorecard
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']

class ClubMatchSerializer(serializers.ModelSerializer):
    team1_details = TeamSerializer(source='team1', read_only=True)
    team2_details = TeamSerializer(source='team2', read_only=True)
    team1_name = serializers.CharField(source='team1.name', read_only=True)
    team2_name = serializers.CharField(source='team2.name', read_only=True)
    turf_name = serializers.CharField(source='turf.name', read_only=True)
    court_name = serializers.CharField(source='court.name', read_only=True)
    winner_name = serializers.CharField(source='winner.name', read_only=True)
    tournament_name = serializers.CharField(source='tournament.name', read_only=True)
    club_name = serializers.CharField(source='club.name', read_only=True)
    club_customization = serializers.JSONField(source='club.customization', read_only=True)
    toss_winner_name = serializers.CharField(source='toss_winner.name', read_only=True)
    timer_state = LiveMatchTimerStateSerializer(read_only=True)
    scorecard = LiveCricketScorecardSerializer(read_only=True)
    ball_type = serializers.SerializerMethodField()
    ground_name = serializers.SerializerMethodField()
    total_overs = serializers.SerializerMethodField()
    venue_type = serializers.SerializerMethodField()
    club_members = serializers.SerializerMethodField()

    class Meta:
        model = ClubMatch
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_ball_type(self, obj):
        return (obj.custom_rules or {}).get('ball_type', 'White Ball')

    def get_ground_name(self, obj):
        if obj.turf:
            return obj.turf.name
        return (obj.custom_rules or {}).get('ground_name', 'Open Ground')

    def get_total_overs(self, obj):
        return int((obj.custom_rules or {}).get('total_overs', 6))

    def get_venue_type(self, obj):
        if obj.turf:
            return 'TURF'
        return (obj.custom_rules or {}).get('venue_type', 'GROUND')

    def get_club_members(self, obj):
        members = obj.club.members.filter(is_active=True).select_related('user')
        return [
            {
                'id': str(m.user.id),
                'name': m.user.full_name or m.user.first_name or m.user.email.split('@')[0],
                'email': m.user.email,
                'role': m.role
            }
            for m in members
        ]

class ClubSerializer(serializers.ModelSerializer):
    owner_details = ClubMemberUserSerializer(source='owner', read_only=True)
    members = ClubMemberSerializer(many=True, read_only=True)
    tournaments = ClubTournamentSerializer(many=True, read_only=True)
    recent_matches = serializers.SerializerMethodField()
    is_owner = serializers.SerializerMethodField()
    user_role = serializers.SerializerMethodField()
    home_turf_name = serializers.CharField(source='home_turf.name', read_only=True)

    class Meta:
        model = Club
        fields = [
            'id', 'name', 'slug', 'description', 'logo', 'banner', 'theme_color',
            'owner', 'owner_details', 'home_turf', 'home_turf_name', 'sport',
            'privacy', 'invite_code', 'customization', 'members', 'tournaments',
            'recent_matches', 'is_owner', 'user_role', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'slug', 'invite_code', 'owner', 'created_at', 'updated_at']

    def get_recent_matches(self, obj):
        recent = obj.matches.order_by('-match_date')[:10]
        return ClubMatchSerializer(recent, many=True, context=self.context).data

    def get_is_owner(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.owner_id == request.user.id
        return False

    def get_user_role(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            member = obj.members.filter(user=request.user).first()
            if member:
                return member.role
            if obj.owner_id == request.user.id:
                return 'OWNER'
        return None
