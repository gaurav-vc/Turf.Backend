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
    team_name = serializers.CharField(source='team.team.name', read_only=True)
    team_color = serializers.CharField(source='team.team.logo_color', default='#3b82f6', read_only=True)

    class Meta:
        model = GroupDrawCard
        fields = '__all__'

class AuctionTournamentConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuctionTournamentConfig
        fields = '__all__'
