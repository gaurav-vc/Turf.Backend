import uuid
from django.db import models
from core.models import BaseModel
from accounts.models import User
from .models import Auction, AuctionTeam, AuctionPlayer

class AuctionTournamentConfig(BaseModel):
    auction = models.OneToOneField(Auction, on_delete=models.CASCADE, related_name='v24_config')
    max_squad = models.IntegerField(default=11)
    min_players = models.IntegerField(default=11)
    max_players = models.IntegerField(default=11)
    reserve_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    additional_kitty = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    penalty_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    category_wise_bidding = models.BooleanField(default=False)
    bring_back_unsold = models.BooleanField(default=True)
    confirm_sale = models.BooleanField(default=False)
    sound_effects = models.BooleanField(default=True)
    sold_animation = models.BooleanField(default=True)
    sold_animation_style = models.CharField(max_length=50, default='Confetti Burst')
    sold_animation_duration = models.IntegerField(default=3)
    highest_bid_animation = models.BooleanField(default=True)
    highest_bid_animation_style = models.CharField(max_length=50, default='Fireworks')
    highest_bid_animation_duration = models.IntegerField(default=5)
    online_timer_enabled = models.BooleanField(default=False)
    timer_seconds = models.IntegerField(default=30)
    closing_wait_seconds = models.IntegerField(default=5)
    auction_background = models.CharField(max_length=255, default='stadium')
    overall_background = models.CharField(max_length=255, default='default')
    tournament_logo = models.CharField(max_length=500, blank=True, null=True)
    category_sequence = models.JSONField(default=list, blank=True)
    completion_message = models.CharField(max_length=255, default='Auction Completed - All teams are now completed')
    custom_bid_enabled = models.BooleanField(default=True)
    live_media_enabled = models.BooleanField(default=False)
    live_media_url = models.CharField(max_length=500, blank=True, null=True)

class AuctionCategory(BaseModel):
    auction = models.ForeignKey(Auction, on_delete=models.CASCADE, related_name='categories')
    name = models.CharField(max_length=100)
    display_order = models.IntegerField(default=1)
    target_count = models.IntegerField(default=0)
    base_price = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    min_bid = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)

    class Meta:
        ordering = ['display_order', 'created_at']
        unique_together = ('auction', 'name')

class BidSlab(BaseModel):
    auction = models.ForeignKey(Auction, on_delete=models.CASCADE, related_name='bid_slabs')
    up_to_bid = models.DecimalField(max_digits=12, decimal_places=2)
    increment = models.DecimalField(max_digits=12, decimal_places=2)
    display_order = models.IntegerField(default=1)

    class Meta:
        ordering = ['display_order', 'up_to_bid']

class SquadRule(BaseModel):
    auction = models.ForeignKey(Auction, on_delete=models.CASCADE, related_name='squad_rules')
    field_key = models.CharField(max_length=100)
    operator = models.CharField(max_length=20, default='minimum') # minimum, maximum, exact
    field_value = models.CharField(max_length=100)
    min_count = models.IntegerField(default=0)
    max_count = models.IntegerField(null=True, blank=True)
    active = models.BooleanField(default=True)
    display_order = models.IntegerField(default=1)

    class Meta:
        ordering = ['display_order', 'created_at']

class CustomFieldDefinition(BaseModel):
    auction = models.ForeignKey(Auction, on_delete=models.CASCADE, related_name='custom_fields')
    entity_type = models.CharField(max_length=20, choices=[('player', 'Player'), ('team', 'Team')])
    field_key = models.CharField(max_length=100)
    label = models.CharField(max_length=100)
    data_type = models.CharField(max_length=20, default='text') # text, number, select, multiselect
    required = models.BooleanField(default=False)
    filterable = models.BooleanField(default=False)
    exportable = models.BooleanField(default=True)
    active = models.BooleanField(default=True)
    display_order = models.IntegerField(default=1)

    class Meta:
        ordering = ['display_order', 'created_at']
        unique_together = ('auction', 'entity_type', 'field_key')

class CustomFieldOption(BaseModel):
    field_definition = models.ForeignKey(CustomFieldDefinition, on_delete=models.CASCADE, related_name='options')
    option_value = models.CharField(max_length=255)
    display_order = models.IntegerField(default=1)

    class Meta:
        ordering = ['display_order', 'created_at']
        unique_together = ('field_definition', 'option_value')

class CustomFieldValue(BaseModel):
    field_definition = models.ForeignKey(CustomFieldDefinition, on_delete=models.CASCADE, related_name='values')
    entity_id = models.UUIDField()
    value_text = models.TextField(blank=True, default='')

    class Meta:
        unique_together = ('field_definition', 'entity_id')

class AuctionPageDesign(BaseModel):
    auction = models.OneToOneField(Auction, on_delete=models.CASCADE, related_name='page_design')
    design_json = models.JSONField(default=dict)

class PublicAuctionLink(BaseModel):
    auction = models.OneToOneField(Auction, on_delete=models.CASCADE, related_name='public_link')
    public_token = models.CharField(max_length=64, unique=True)
    enabled = models.BooleanField(default=True)
    settings_json = models.JSONField(default=dict)

class PlayerRegistrationLink(BaseModel):
    auction = models.OneToOneField(Auction, on_delete=models.CASCADE, related_name='registration_link')
    registration_token = models.CharField(max_length=64, unique=True)
    enabled = models.BooleanField(default=True)
    title = models.CharField(max_length=255, default='Player Registration')
    intro_text = models.TextField(default='Register to participate in this tournament auction.')
    success_message = models.TextField(default='Thank you. Your player registration has been submitted successfully.')
    show_tournament_logo = models.BooleanField(default=True)
    show_tournament_name = models.BooleanField(default=True)
    fields_json = models.JSONField(default=list)

class AuctionSponsorItem(BaseModel):
    auction = models.ForeignKey(Auction, on_delete=models.CASCADE, related_name='sponsors')
    source_url = models.CharField(max_length=500)
    title = models.CharField(max_length=255, blank=True, default='')
    display_order = models.IntegerField(default=1)
    duration_seconds = models.IntegerField(default=10)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ['display_order', 'created_at']

class AuctionMediaItem(BaseModel):
    auction = models.ForeignKey(Auction, on_delete=models.CASCADE, related_name='media_items')
    media_type = models.CharField(max_length=20, default='image') # image, video
    source_url = models.CharField(max_length=500)
    title = models.CharField(max_length=255, blank=True, default='')
    display_order = models.IntegerField(default=1)
    duration_seconds = models.IntegerField(default=10)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ['display_order', 'created_at']

class AuctionOverlay(BaseModel):
    auction = models.ForeignKey(Auction, on_delete=models.CASCADE, related_name='overlays')
    name = models.CharField(max_length=100)
    overlay_type = models.CharField(max_length=50, default='lower_third') # lower_third, scoreboard, sponsor_strip
    design_json = models.JSONField(default=dict)
    enabled = models.BooleanField(default=True)

class GroupDrawCard(BaseModel):
    auction = models.ForeignKey(Auction, on_delete=models.CASCADE, related_name='group_cards')
    card_number = models.IntegerField()
    group_name = models.CharField(max_length=100)
    team = models.ForeignKey(AuctionTeam, on_delete=models.SET_NULL, null=True, blank=True, related_name='draw_cards')
    revealed = models.BooleanField(default=False)

    class Meta:
        ordering = ['card_number']
        unique_together = ('auction', 'card_number')

class AuctionEventLog(BaseModel):
    auction = models.ForeignKey(Auction, on_delete=models.CASCADE, related_name='events')
    lot_player = models.ForeignKey(AuctionPlayer, on_delete=models.SET_NULL, null=True, blank=True)
    team = models.ForeignKey(AuctionTeam, on_delete=models.SET_NULL, null=True, blank=True)
    event_type = models.CharField(max_length=50) # BID, SOLD, UNSOLD, UNDO_BID, UNDO_SALE, REAUCTION_STARTED, etc.
    amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at']

class TeamPurseTransaction(BaseModel):
    auction = models.ForeignKey(Auction, on_delete=models.CASCADE, related_name='purse_transactions')
    team = models.ForeignKey(AuctionTeam, on_delete=models.CASCADE, related_name='purse_transactions')
    player = models.ForeignKey(AuctionPlayer, on_delete=models.SET_NULL, null=True, blank=True)
    transaction_type = models.CharField(max_length=50) # Sale, Undo Sale, Penalty, Kitty Adjustment
    amount = models.DecimalField(max_digits=12, decimal_places=2) # negative for sales, positive for refunds
    note = models.CharField(max_length=255, blank=True, default='')

    class Meta:
        ordering = ['-created_at']
