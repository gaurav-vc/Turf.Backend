from django.contrib import admin
from .models import Auction, AuctionTeam, AuctionPlayer, Bid

class AuctionTeamInline(admin.TabularInline):
    model = AuctionTeam
    extra = 1

class AuctionPlayerInline(admin.TabularInline):
    model = AuctionPlayer
    extra = 1

@admin.register(Auction)
class AuctionAdmin(admin.ModelAdmin):
    list_display = ('name', 'organizer', 'status', 'base_budget', 'active_player')
    list_filter = ('status',)
    search_fields = ('name',)
    inlines = [AuctionTeamInline, AuctionPlayerInline]

@admin.register(AuctionTeam)
class AuctionTeamAdmin(admin.ModelAdmin):
    list_display = ('team', 'auction', 'remaining_budget')
    list_filter = ('auction',)
    search_fields = ('team__name',)

@admin.register(AuctionPlayer)
class AuctionPlayerAdmin(admin.ModelAdmin):
    list_display = ('player', 'auction', 'base_price', 'sold_price', 'sold_to', 'status')
    list_filter = ('status', 'auction')
    search_fields = ('player__first_name', 'player__last_name', 'player__username')

@admin.register(Bid)
class BidAdmin(admin.ModelAdmin):
    list_display = ('auction_player', 'team', 'amount', 'created_at')
    list_filter = ('auction_player__auction',)
    search_fields = ('team__team__name',)

from .models_v24 import (
    AuctionTournamentConfig,
    AuctionCategory,
    BidSlab,
    SquadRule,
    CustomFieldDefinition,
    CustomFieldOption,
    AuctionPageDesign,
    PublicAuctionLink,
    PlayerRegistrationLink,
    GroupDrawCard,
    AuctionSponsorItem,
    AuctionMediaItem,
    AuctionEventLog,
)

@admin.register(AuctionTournamentConfig)
class AuctionTournamentConfigAdmin(admin.ModelAdmin):
    list_display = ('auction', 'max_squad', 'reserve_amount', 'category_wise_bidding')

@admin.register(AuctionCategory)
class AuctionCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'auction', 'target_count', 'base_price', 'display_order')
    list_filter = ('auction',)

@admin.register(BidSlab)
class BidSlabAdmin(admin.ModelAdmin):
    list_display = ('auction', 'up_to_bid', 'increment', 'display_order')
    list_filter = ('auction',)

@admin.register(SquadRule)
class SquadRuleAdmin(admin.ModelAdmin):
    list_display = ('auction', 'field_key', 'operator', 'field_value', 'min_count', 'max_count', 'active')
    list_filter = ('auction', 'active')

@admin.register(CustomFieldDefinition)
class CustomFieldDefinitionAdmin(admin.ModelAdmin):
    list_display = ('label', 'field_key', 'entity_type', 'data_type', 'required', 'auction')
    list_filter = ('entity_type', 'data_type', 'auction')

@admin.register(CustomFieldOption)
class CustomFieldOptionAdmin(admin.ModelAdmin):
    list_display = ('field_definition', 'option_value', 'display_order')

@admin.register(AuctionPageDesign)
class AuctionPageDesignAdmin(admin.ModelAdmin):
    list_display = ('auction', 'updated_at')

@admin.register(PublicAuctionLink)
class PublicAuctionLinkAdmin(admin.ModelAdmin):
    list_display = ('auction', 'public_token', 'enabled')

@admin.register(PlayerRegistrationLink)
class PlayerRegistrationLinkAdmin(admin.ModelAdmin):
    list_display = ('auction', 'registration_token', 'enabled')

@admin.register(GroupDrawCard)
class GroupDrawCardAdmin(admin.ModelAdmin):
    list_display = ('auction', 'card_number', 'group_name', 'team', 'revealed')
    list_filter = ('auction', 'revealed')

@admin.register(AuctionSponsorItem)
class AuctionSponsorItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'auction', 'display_order', 'duration_seconds', 'active')
    list_filter = ('auction', 'active')

@admin.register(AuctionMediaItem)
class AuctionMediaItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'auction', 'media_type', 'display_order', 'duration_seconds', 'active')
    list_filter = ('auction', 'media_type', 'active')

@admin.register(AuctionEventLog)
class AuctionEventLogAdmin(admin.ModelAdmin):
    list_display = ('auction', 'event_type', 'lot_player', 'team', 'amount', 'created_at')
    list_filter = ('auction', 'event_type')
    ordering = ('-created_at',)

