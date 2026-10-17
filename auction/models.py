from django.db import models
from core.models import BaseModel
from accounts.models import User
from sports.models import Team

class Auction(BaseModel):
    name = models.CharField(max_length=255)
    organizer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='organized_auctions')
    tournament = models.ForeignKey('sports.Tournament', on_delete=models.SET_NULL, null=True, blank=True, related_name='auctions')
    base_budget = models.DecimalField(max_digits=12, decimal_places=2, default=50000.00)
    status = models.CharField(max_length=20, choices=[
        ('PENDING', 'Pending'),
        ('ACTIVE', 'Active'),
        ('COMPLETED', 'Completed')
    ], default='PENDING')
    active_player = models.ForeignKey('AuctionPlayer', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')

class AuctionTeam(BaseModel):
    auction = models.ForeignKey(Auction, on_delete=models.CASCADE, related_name='teams')
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    remaining_budget = models.DecimalField(max_digits=12, decimal_places=2)
    # Phase 2 V24 additions (Optional & Backward-Compatible)
    additional_kitty = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    penalty_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    reserve_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    custom_data = models.JSONField(default=dict, blank=True)
    live_token = models.CharField(max_length=64, blank=True, null=True, unique=True)

class AuctionPlayer(BaseModel):
    auction = models.ForeignKey(Auction, on_delete=models.CASCADE, related_name='players')
    player = models.ForeignKey(User, on_delete=models.CASCADE)
    base_price = models.DecimalField(max_digits=10, decimal_places=2, default=1000.00)
    sold_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    sold_to = models.ForeignKey(AuctionTeam, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=[
        ('AVAILABLE', 'Available'),
        ('BIDDING', 'Bidding'),
        ('SOLD', 'Sold'),
        ('UNSOLD', 'Unsold')
    ], default='AVAILABLE')
    # Phase 2 V24 additions (Optional & Backward-Compatible)
    serial_no = models.IntegerField(null=True, blank=True)
    photo_url = models.CharField(max_length=500, blank=True, null=True)
    category = models.CharField(max_length=100, blank=True, null=True)
    role = models.CharField(max_length=100, blank=True, null=True)
    batting_style = models.CharField(max_length=100, blank=True, null=True)
    bowling_style = models.CharField(max_length=100, blank=True, null=True)
    location = models.CharField(max_length=150, blank=True, null=True)
    mobile = models.CharField(max_length=30, blank=True, null=True)
    age = models.IntegerField(null=True, blank=True)
    custom_data = models.JSONField(default=dict, blank=True)
    registration_source = models.CharField(max_length=50, default='Manual')
    reauction_round_seen = models.IntegerField(default=0)
    
class Bid(BaseModel):
    auction_player = models.ForeignKey(AuctionPlayer, on_delete=models.CASCADE, related_name='bids')
    team = models.ForeignKey(AuctionTeam, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    bid_type = models.CharField(max_length=50, default='Team Button')

# Import all Phase 2 models
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

