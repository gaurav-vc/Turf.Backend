# Generated for Tournament-Specific Live Auction Association
import django.db.models.deletion
from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('auction', '0002_phase2_v24_models'),
        ('sports', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='auction',
            name='tournament',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='auctions',
                to='sports.tournament'
            ),
        ),
    ]
