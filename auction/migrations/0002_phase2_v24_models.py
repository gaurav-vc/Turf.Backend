# Generated for Phase 2 V24 Cricket Auction Extension
import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('auction', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # --- Additive fields on existing models ---
        migrations.AddField(
            model_name='auctionteam',
            name='additional_kitty',
            field=models.DecimalField(decimal_places=2, default=0.0, max_digits=12),
        ),
        migrations.AddField(
            model_name='auctionteam',
            name='penalty_amount',
            field=models.DecimalField(decimal_places=2, default=0.0, max_digits=12),
        ),
        migrations.AddField(
            model_name='auctionteam',
            name='reserve_amount',
            field=models.DecimalField(decimal_places=2, default=0.0, max_digits=12),
        ),
        migrations.AddField(
            model_name='auctionteam',
            name='custom_data',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='auctionteam',
            name='live_token',
            field=models.CharField(blank=True, max_length=64, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='auctionplayer',
            name='serial_no',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='auctionplayer',
            name='photo_url',
            field=models.CharField(blank=True, max_length=500, null=True),
        ),
        migrations.AddField(
            model_name='auctionplayer',
            name='category',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='auctionplayer',
            name='role',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='auctionplayer',
            name='batting_style',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='auctionplayer',
            name='bowling_style',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='auctionplayer',
            name='location',
            field=models.CharField(blank=True, max_length=150, null=True),
        ),
        migrations.AddField(
            model_name='auctionplayer',
            name='mobile',
            field=models.CharField(blank=True, max_length=30, null=True),
        ),
        migrations.AddField(
            model_name='auctionplayer',
            name='age',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='auctionplayer',
            name='custom_data',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='auctionplayer',
            name='registration_source',
            field=models.CharField(default='Manual', max_length=50),
        ),
        migrations.AddField(
            model_name='auctionplayer',
            name='reauction_round_seen',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='bid',
            name='bid_type',
            field=models.CharField(default='Team Button', max_length=50),
        ),

        # --- New Phase 2 V24 Models ---
        migrations.CreateModel(
            name='AuctionTournamentConfig',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(default=True)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('max_squad', models.IntegerField(default=11)),
                ('min_players', models.IntegerField(default=11)),
                ('max_players', models.IntegerField(default=11)),
                ('reserve_amount', models.DecimalField(decimal_places=2, default=0.0, max_digits=12)),
                ('additional_kitty', models.DecimalField(decimal_places=2, default=0.0, max_digits=12)),
                ('penalty_amount', models.DecimalField(decimal_places=2, default=0.0, max_digits=12)),
                ('category_wise_bidding', models.BooleanField(default=False)),
                ('bring_back_unsold', models.BooleanField(default=True)),
                ('confirm_sale', models.BooleanField(default=False)),
                ('sound_effects', models.BooleanField(default=True)),
                ('sold_animation', models.BooleanField(default=True)),
                ('sold_animation_style', models.CharField(default='Confetti Burst', max_length=50)),
                ('sold_animation_duration', models.IntegerField(default=3)),
                ('highest_bid_animation', models.BooleanField(default=True)),
                ('highest_bid_animation_style', models.CharField(default='Fireworks', max_length=50)),
                ('highest_bid_animation_duration', models.IntegerField(default=5)),
                ('online_timer_enabled', models.BooleanField(default=False)),
                ('timer_seconds', models.IntegerField(default=30)),
                ('closing_wait_seconds', models.IntegerField(default=5)),
                ('auction_background', models.CharField(default='stadium', max_length=255)),
                ('overall_background', models.CharField(default='default', max_length=255)),
                ('tournament_logo', models.CharField(blank=True, max_length=500, null=True)),
                ('category_sequence', models.JSONField(blank=True, default=list)),
                ('completion_message', models.CharField(default='Auction Completed - All teams are now completed', max_length=255)),
                ('custom_bid_enabled', models.BooleanField(default=True)),
                ('live_media_enabled', models.BooleanField(default=False)),
                ('live_media_url', models.CharField(blank=True, max_length=500, null=True)),
                ('auction', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='v24_config', to='auction.auction')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={'abstract': False},
        ),

        migrations.CreateModel(
            name='AuctionCategory',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(default=True)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('name', models.CharField(max_length=100)),
                ('display_order', models.IntegerField(default=1)),
                ('target_count', models.IntegerField(default=0)),
                ('base_price', models.DecimalField(decimal_places=2, default=0.0, max_digits=12)),
                ('min_bid', models.DecimalField(decimal_places=2, default=0.0, max_digits=12)),
                ('auction', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='categories', to='auction.auction')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['display_order', 'created_at'],
                'unique_together': {('auction', 'name')},
            },
        ),

        migrations.CreateModel(
            name='BidSlab',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(default=True)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('up_to_bid', models.DecimalField(decimal_places=2, max_digits=12)),
                ('increment', models.DecimalField(decimal_places=2, max_digits=12)),
                ('display_order', models.IntegerField(default=1)),
                ('auction', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bid_slabs', to='auction.auction')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['display_order', 'up_to_bid'],
            },
        ),

        migrations.CreateModel(
            name='SquadRule',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(default=True)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('field_key', models.CharField(max_length=100)),
                ('operator', models.CharField(default='minimum', max_length=20)),
                ('field_value', models.CharField(max_length=100)),
                ('min_count', models.IntegerField(default=0)),
                ('max_count', models.IntegerField(blank=True, null=True)),
                ('active', models.BooleanField(default=True)),
                ('display_order', models.IntegerField(default=1)),
                ('auction', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='squad_rules', to='auction.auction')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['display_order', 'created_at'],
            },
        ),

        migrations.CreateModel(
            name='CustomFieldDefinition',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(default=True)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('entity_type', models.CharField(choices=[('player', 'Player'), ('team', 'Team')], max_length=20)),
                ('field_key', models.CharField(max_length=100)),
                ('label', models.CharField(max_length=100)),
                ('data_type', models.CharField(default='text', max_length=20)),
                ('required', models.BooleanField(default=False)),
                ('filterable', models.BooleanField(default=False)),
                ('exportable', models.BooleanField(default=True)),
                ('active', models.BooleanField(default=True)),
                ('display_order', models.IntegerField(default=1)),
                ('auction', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='custom_fields', to='auction.auction')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['display_order', 'created_at'],
                'unique_together': {('auction', 'entity_type', 'field_key')},
            },
        ),

        migrations.CreateModel(
            name='CustomFieldOption',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(default=True)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('option_value', models.CharField(max_length=255)),
                ('display_order', models.IntegerField(default=1)),
                ('field_definition', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='options', to='auction.customfielddefinition')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['display_order', 'created_at'],
                'unique_together': {('field_definition', 'option_value')},
            },
        ),

        migrations.CreateModel(
            name='CustomFieldValue',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(default=True)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('entity_id', models.UUIDField()),
                ('value_text', models.TextField(blank=True, default='')),
                ('field_definition', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='values', to='auction.customfielddefinition')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'unique_together': {('field_definition', 'entity_id')},
            },
        ),

        migrations.CreateModel(
            name='AuctionPageDesign',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(default=True)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('design_json', models.JSONField(default=dict)),
                ('auction', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='page_design', to='auction.auction')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={'abstract': False},
        ),

        migrations.CreateModel(
            name='PublicAuctionLink',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(default=True)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('public_token', models.CharField(max_length=64, unique=True)),
                ('enabled', models.BooleanField(default=True)),
                ('settings_json', models.JSONField(default=dict)),
                ('auction', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='public_link', to='auction.auction')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={'abstract': False},
        ),

        migrations.CreateModel(
            name='PlayerRegistrationLink',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(default=True)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('registration_token', models.CharField(max_length=64, unique=True)),
                ('enabled', models.BooleanField(default=True)),
                ('title', models.CharField(default='Player Registration', max_length=255)),
                ('intro_text', models.TextField(default='Register to participate in this tournament auction.')),
                ('success_message', models.TextField(default='Thank you. Your player registration has been submitted successfully.')),
                ('show_tournament_logo', models.BooleanField(default=True)),
                ('show_tournament_name', models.BooleanField(default=True)),
                ('fields_json', models.JSONField(default=list)),
                ('auction', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='registration_link', to='auction.auction')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={'abstract': False},
        ),

        migrations.CreateModel(
            name='AuctionSponsorItem',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(default=True)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('source_url', models.CharField(max_length=500)),
                ('title', models.CharField(blank=True, default='', max_length=255)),
                ('display_order', models.IntegerField(default=1)),
                ('duration_seconds', models.IntegerField(default=10)),
                ('active', models.BooleanField(default=True)),
                ('auction', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sponsors', to='auction.auction')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['display_order', 'created_at'],
            },
        ),

        migrations.CreateModel(
            name='AuctionMediaItem',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(default=True)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('media_type', models.CharField(default='image', max_length=20)),
                ('source_url', models.CharField(max_length=500)),
                ('title', models.CharField(blank=True, default='', max_length=255)),
                ('display_order', models.IntegerField(default=1)),
                ('duration_seconds', models.IntegerField(default=10)),
                ('active', models.BooleanField(default=True)),
                ('auction', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='media_items', to='auction.auction')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['display_order', 'created_at'],
            },
        ),

        migrations.CreateModel(
            name='AuctionOverlay',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(default=True)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('name', models.CharField(max_length=100)),
                ('overlay_type', models.CharField(default='lower_third', max_length=50)),
                ('design_json', models.JSONField(default=dict)),
                ('enabled', models.BooleanField(default=True)),
                ('auction', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='overlays', to='auction.auction')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={'abstract': False},
        ),

        migrations.CreateModel(
            name='GroupDrawCard',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(default=True)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('card_number', models.IntegerField()),
                ('group_name', models.CharField(max_length=100)),
                ('revealed', models.BooleanField(default=False)),
                ('auction', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='group_cards', to='auction.auction')),
                ('team', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='draw_cards', to='auction.auctionteam')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['card_number'],
                'unique_together': {('auction', 'card_number')},
            },
        ),

        migrations.CreateModel(
            name='AuctionEventLog',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(default=True)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('event_type', models.CharField(max_length=50)),
                ('amount', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ('details', models.JSONField(blank=True, default=dict)),
                ('auction', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='events', to='auction.auction')),
                ('lot_player', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='auction.auctionplayer')),
                ('team', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='auction.auctionteam')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),

        migrations.CreateModel(
            name='TeamPurseTransaction',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(default=True)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('transaction_type', models.CharField(max_length=50)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12)),
                ('note', models.CharField(blank=True, default='', max_length=255)),
                ('auction', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='purse_transactions', to='auction.auction')),
                ('team', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='purse_transactions', to='auction.auctionteam')),
                ('player', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='auction.auctionplayer')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
