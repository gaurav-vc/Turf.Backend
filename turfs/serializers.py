from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import Turf, Court, BlockedPeriod, PriceRule

User = get_user_model()

class TurfSerializer(serializers.ModelSerializer):
    owner = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), required=False, allow_null=True)
    class Meta:
        model = Turf
        fields = '__all__'

class CourtSerializer(serializers.ModelSerializer):
    class Meta:
        model = Court
        fields = '__all__'

class BlockedPeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlockedPeriod
        fields = '__all__'

class PriceRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = PriceRule
        fields = '__all__'
