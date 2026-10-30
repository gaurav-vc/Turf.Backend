from rest_framework import serializers
from .models import Auction, AuctionTeam, AuctionPlayer, Bid
from .models_v24 import (
    AuctionTournamentConfig,
    AuctionCategory,
    BidSlab,
    SquadRule,
    CustomFieldDefinition,
    CustomFieldOption,
    CustomFieldValue,
    AuctionPageDesign,
    PublicAuctionLink,
    PlayerRegistrationLink,
    AuctionSponsorItem,
    AuctionMediaItem,
    AuctionOverlay,
    GroupDrawCard,
    AuctionEventLog,
    TeamPurseTransaction,
)

class AuctionCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = AuctionCategory
        fields = '__all__'

class BidSlabSerializer(serializers.ModelSerializer):
    class Meta:
        model = BidSlab
        fields = '__all__'

class SquadRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = SquadRule
        fields = '__all__'

class CustomFieldOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomFieldOption
        fields = '__all__'

class CustomFieldDefinitionSerializer(serializers.ModelSerializer):
    options = CustomFieldOptionSerializer(many=True, read_only=True)

    class Meta:
        model = CustomFieldDefinition
        fields = '__all__'

class AuctionPageDesignSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuctionPageDesign
        fields = '__all__'

class PublicAuctionLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = PublicAuctionLink
        fields = '__all__'

class PlayerRegistrationLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlayerRegistrationLink
        fields = '__all__'

class AuctionSponsorItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuctionSponsorItem
        fields = '__all__'

class AuctionMediaItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuctionMediaItem
        fields = '__all__'

class AuctionOverlaySerializer(serializers.ModelSerializer):
    class Meta:
        model = AuctionOverlay
        fields = '__all__'

class GroupDrawCardSerializer(serializers.ModelSerializer):
    team_name = serializers.SerializerMethodField()
    team_color = serializers.SerializerMethodField()
    team_short_name = serializers.SerializerMethodField()
    team_logo = serializers.SerializerMethodField()

    class Meta:
        model = GroupDrawCard
        fields = '__all__'

    def get_team_name(self, obj):
        if not obj.team:
            return None
        if obj.team.team and getattr(obj.team.team, 'name', None):
            return obj.team.team.name
        if getattr(obj.team, 'custom_data', None):
            return obj.team.custom_data.get('team_name', '')
        return 'Team'

    def get_team_short_name(self, obj):
        if not obj.team:
            return None
        if getattr(obj.team, 'custom_data', None) and obj.team.custom_data.get('short_name'):
            return obj.team.custom_data.get('short_name')
        t_name = self.get_team_name(obj) or 'TM'
        return t_name[:3].upper()

    def get_team_color(self, obj):
        if not obj.team:
            return '#3b82f6'
        if getattr(obj.team, 'custom_data', None) and obj.team.custom_data.get('color'):
            return obj.team.custom_data.get('color')
        if obj.team.team and getattr(obj.team.team, 'logo_color', None):
            return obj.team.team.logo_color
        return '#3b82f6'

    def get_team_logo(self, obj):
        if not obj.team:
            return None
        request = self.context.get('request')
        if obj.team.team and getattr(obj.team.team, 'logo', None):
            try:
                url = obj.team.team.logo.url
                return request.build_absolute_uri(url) if request else url
            except Exception:
                pass
        if getattr(obj.team, 'custom_data', None):
            c_logo = obj.team.custom_data.get('logo_url') or obj.team.custom_data.get('logo')
            if c_logo:
                if request and not (c_logo.startswith('http://') or c_logo.startswith('https://')):
                    return request.build_absolute_uri(c_logo)
                return c_logo
        return None

class AuctionTournamentConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuctionTournamentConfig
        fields = '__all__'
