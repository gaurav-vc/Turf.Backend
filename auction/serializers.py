from rest_framework import serializers
from .models import Auction, AuctionTeam, AuctionPlayer, Bid
from accounts.models import User

class SimplePlayerSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()
    sold_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = AuctionPlayer
        fields = ['id', 'name', 'role', 'base_price', 'sold_price', 'status']

    def get_name(self, obj):
        if obj.player:
            return obj.player.full_name or obj.player.first_name or obj.player.username or obj.player.email.split('@')[0]
        return "Unknown Player"

    def get_role(self, obj):
        if hasattr(obj.player, 'profile') and obj.player.profile:
            pref = obj.player.profile.preferences or {}
            if 'role' in pref:
                return pref['role']
            role_obj = obj.player.profile.sport_roles.first()
            if role_obj:
                return role_obj.role
        return "All-Rounder"

class AuctionTeamSerializer(serializers.ModelSerializer):
    team_name = serializers.CharField(source='team.name', read_only=True)
    team_color = serializers.CharField(source='team.logo_color', default='#3b82f6', read_only=True)
    captain_name = serializers.SerializerMethodField()
    captain_email = serializers.SerializerMethodField()
    players_count = serializers.SerializerMethodField()
    acquired_players = serializers.SerializerMethodField()

    class Meta:
        model = AuctionTeam
        fields = '__all__'

    def get_captain_name(self, obj):
        if obj.team and obj.team.user:
            user = obj.team.user
            return user.full_name or user.first_name or user.email.split('@')[0]
        return "Team Captain"

    def get_captain_email(self, obj):
        if obj.team and obj.team.user:
            return obj.team.user.email
        return ""

    def get_players_count(self, obj):
        return obj.auction.players.filter(sold_to=obj).count()

    def get_acquired_players(self, obj):
        players = obj.auction.players.filter(sold_to=obj)
        return SimplePlayerSerializer(players, many=True).data

class BidSerializer(serializers.ModelSerializer):
    team_name = serializers.CharField(source='team.team.name', read_only=True)
    captain_name = serializers.SerializerMethodField()

    class Meta:
        model = Bid
        fields = '__all__'

    def get_captain_name(self, obj):
        if obj.team and obj.team.team and obj.team.team.user:
            user = obj.team.team.user
            return user.full_name or user.first_name or user.email.split('@')[0]
        return "Captain"

class AuctionPlayerSerializer(serializers.ModelSerializer):
    player_name = serializers.SerializerMethodField()
    player_skills = serializers.SerializerMethodField()
    tier = serializers.SerializerMethodField()
    sold_to_name = serializers.CharField(source='sold_to.team.name', read_only=True)
    highest_bid = serializers.SerializerMethodField()
    bids = serializers.SerializerMethodField()
    
    class Meta:
        model = AuctionPlayer
        fields = '__all__'

    def get_player_name(self, obj):
        if obj.player:
            return obj.player.full_name or obj.player.first_name or obj.player.username or obj.player.email.split('@')[0]
        return "Unknown Player"

    def get_player_skills(self, obj):
        if hasattr(obj.player, 'profile') and obj.player.profile:
            pref = obj.player.profile.preferences or {}
            if 'role' in pref:
                return pref['role']
            role_obj = obj.player.profile.sport_roles.first()
            if role_obj:
                return role_obj.role
        return "All-Rounder"

    def get_tier(self, obj):
        if hasattr(obj.player, 'profile') and obj.player.profile:
            pref = obj.player.profile.preferences or {}
            return pref.get('tier', 'Standard')
        return "Standard"

    def get_highest_bid(self, obj):
        bid = obj.bids.order_by('-amount').first()
        if bid:
            return BidSerializer(bid).data
        return None

    def get_bids(self, obj):
        bids = obj.bids.order_by('-amount')[:10]
        return BidSerializer(bids, many=True).data

class AuctionSerializer(serializers.ModelSerializer):
    teams = AuctionTeamSerializer(many=True, read_only=True)
    players = AuctionPlayerSerializer(many=True, read_only=True)
    active_player_detail = AuctionPlayerSerializer(source='active_player', read_only=True)
    organizer_name = serializers.SerializerMethodField()
    recent_bids = serializers.SerializerMethodField()

    class Meta:
        model = Auction
        fields = '__all__'

    def get_organizer_name(self, obj):
        if obj.organizer:
            return obj.organizer.full_name or obj.organizer.first_name or obj.organizer.email.split('@')[0]
        return "Organizer"

    def get_recent_bids(self, obj):
        # Fetch the latest bids across all players in this auction
        bids = Bid.objects.filter(auction_player__auction=obj).order_by('-created_at')[:15]
        return BidSerializer(bids, many=True).data

