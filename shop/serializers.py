import json
from django.db import models
from rest_framework import serializers
from .models import Product, ShopOrder, OrderItem, ProductReview

class ProductReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    user_email = serializers.SerializerMethodField()
    user_avatar = serializers.SerializerMethodField()

    class Meta:
        model = ProductReview
        fields = [
            'id', 'product', 'user', 'user_name', 'user_email', 
            'user_avatar', 'rating', 'comment', 'verified_purchase', 
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'verified_purchase', 'created_at', 'updated_at']

    def get_user_name(self, obj):
        if hasattr(obj.user, 'full_name') and obj.user.full_name:
            return obj.user.full_name
        return getattr(obj.user, 'username', '') or getattr(obj.user, 'email', '').split('@')[0]

    def get_user_email(self, obj):
        return getattr(obj.user, 'email', '')

    def get_user_avatar(self, obj):
        return getattr(obj.user, 'avatar', None)

class ProductSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    category = serializers.SerializerMethodField()
    sport = serializers.SerializerMethodField()
    badge = serializers.SerializerMethodField()
    rating = serializers.SerializerMethodField()
    reviews_count = serializers.SerializerMethodField()
    reviews = serializers.SerializerMethodField()
    user_has_purchased = serializers.SerializerMethodField()
    user_review = serializers.SerializerMethodField()
    is_customizable = serializers.SerializerMethodField()
    sizes = serializers.SerializerMethodField()
    features = serializers.SerializerMethodField()
    display_description = serializers.SerializerMethodField()
    original_price = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = '__all__'

    def _get_meta(self, obj):
        if not obj.description:
            return {}
        try:
            if obj.description.strip().startswith('{'):
                return json.loads(obj.description)
        except Exception:
            pass
        return {}

    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        meta = self._get_meta(obj)
        if 'image_url' in meta and meta['image_url']:
            return meta['image_url']
        return ""

    def get_category(self, obj):
        meta = self._get_meta(obj)
        if 'category' in meta and meta['category']:
            return meta['category']
        return "General"

    def get_sport(self, obj):
        meta = self._get_meta(obj)
        if 'sport' in meta and meta['sport']:
            return meta['sport']
        return "Multi-Sport"

    def get_badge(self, obj):
        meta = self._get_meta(obj)
        return meta.get('badge', '')

    def get_rating(self, obj):
        try:
            active_reviews = obj.reviews.filter(is_active=True)
            if active_reviews.exists():
                avg = active_reviews.aggregate(models.Avg('rating'))['rating__avg']
                if avg is not None:
                    return round(float(avg), 1)
        except Exception:
            pass
        return None

    def get_reviews_count(self, obj):
        try:
            return obj.reviews.filter(is_active=True).count()
        except Exception:
            return 0

    def get_reviews(self, obj):
        try:
            active_reviews = obj.reviews.filter(is_active=True).order_by('-created_at')[:20]
            return ProductReviewSerializer(active_reviews, many=True).data
        except Exception:
            return []

    def get_user_has_purchased(self, obj):
        request = self.context.get('request')
        if not request or not request.user or not request.user.is_authenticated:
            return False
        if getattr(request.user, 'user_type', '') in ['ADMIN', 'MANAGER'] or getattr(request.user, 'is_staff', False):
            return True
        try:
            return ShopOrder.objects.filter(user=request.user, items__product=obj).exists()
        except Exception:
            return False

    def get_user_review(self, obj):
        request = self.context.get('request')
        if not request or not request.user or not request.user.is_authenticated:
            return None
        try:
            rev = obj.reviews.filter(user=request.user, is_active=True).first()
            if rev:
                return ProductReviewSerializer(rev).data
        except Exception:
            pass
        return None



    def get_is_customizable(self, obj):
        meta = self._get_meta(obj)
        if 'is_customizable' in meta:
            return bool(meta['is_customizable'])
        return False

    def get_sizes(self, obj):
        meta = self._get_meta(obj)
        if 'sizes' in meta and isinstance(meta['sizes'], list):
            return meta['sizes']
        return []

    def get_features(self, obj):
        meta = self._get_meta(obj)
        if 'features' in meta and isinstance(meta['features'], list):
            return meta['features']
        return []

    def get_display_description(self, obj):
        meta = self._get_meta(obj)
        if 'description_text' in meta and meta['description_text']:
            return meta['description_text']
        if obj.description and not obj.description.strip().startswith('{'):
            return obj.description
        return ""

    def get_original_price(self, obj):
        meta = self._get_meta(obj)
        if 'original_price' in meta and meta['original_price'] not in [None, '']:
            try:
                return float(meta['original_price'])
            except (ValueError, TypeError):
                pass
        return None

class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_price = serializers.DecimalField(source='product.base_price', max_digits=10, decimal_places=2, read_only=True)
    product_image = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = '__all__'
        read_only_fields = ['order']

    def get_product_image(self, obj):
        if not obj.product:
            return ""
        if obj.product.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.product.image.url)
            return obj.product.image.url
        if obj.product.description and obj.product.description.strip().startswith('{'):
            try:
                meta = json.loads(obj.product.description)
                return meta.get('image_url', '') or ''
            except Exception:
                pass
        return ""

class ShopOrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    customer_name = serializers.SerializerMethodField()
    customer_email = serializers.SerializerMethodField()
    customer_phone = serializers.SerializerMethodField()
    items_count = serializers.SerializerMethodField()
    delivery_type = serializers.SerializerMethodField()
    shipping_address = serializers.SerializerMethodField()
    carrier = serializers.SerializerMethodField()
    tracking_number = serializers.SerializerMethodField()
    estimated_delivery = serializers.SerializerMethodField()
    tracking_notes = serializers.SerializerMethodField()
    tracking_timeline = serializers.SerializerMethodField()

    class Meta:
        model = ShopOrder
        fields = '__all__'
        read_only_fields = ['user']

    def _get_delivery_meta(self, obj):
        raw = obj.delivery_address or ""
        if raw.strip().startswith('{'):
            try:
                return json.loads(raw)
            except Exception:
                pass
        del_type = 'VENUE_PICKUP'
        addr = raw
        if raw.startswith('['):
            end_idx = raw.find(']')
            if end_idx != -1:
                del_type = raw[1:end_idx]
                addr = raw[end_idx+1:].strip()
        return {
            'delivery_type': del_type,
            'address': addr,
            'carrier': 'Turf Venue Desk' if del_type == 'VENUE_PICKUP' else 'Standard Courier',
            'tracking_number': f"TRK-{str(obj.id)[:8].upper()}",
            'estimated_delivery': '',
            'notes': ''
        }

    def get_customer_name(self, obj):
        if not obj.user:
            return "Guest"
        return obj.user.full_name or obj.user.username or obj.user.email

    def get_customer_email(self, obj):
        return obj.user.email if obj.user else ""

    def get_customer_phone(self, obj):
        if not obj.user:
            return ""
        return getattr(obj.user, 'phone', '') or ''

    def get_items_count(self, obj):
        return sum(item.quantity for item in obj.items.all())

    def get_delivery_type(self, obj):
        meta = self._get_delivery_meta(obj)
        return meta.get('delivery_type', 'VENUE_PICKUP')

    def get_shipping_address(self, obj):
        meta = self._get_delivery_meta(obj)
        return meta.get('address', '') or (obj.delivery_address or 'Turf Arena Collection Counter')

    def get_carrier(self, obj):
        meta = self._get_delivery_meta(obj)
        return meta.get('carrier', 'Turf Express')

    def get_tracking_number(self, obj):
        meta = self._get_delivery_meta(obj)
        return meta.get('tracking_number', f"TRK-{str(obj.id)[:8].upper()}")

    def get_estimated_delivery(self, obj):
        meta = self._get_delivery_meta(obj)
        return meta.get('estimated_delivery', '')

    def get_tracking_notes(self, obj):
        meta = self._get_delivery_meta(obj)
        return meta.get('notes', '')

    def get_tracking_timeline(self, obj):
        meta = self._get_delivery_meta(obj)
        steps = [
            {
                'key': 'PENDING',
                'title': 'Order Placed',
                'description': 'Order was submitted and verified.',
                'timestamp': obj.created_at.isoformat() if obj.created_at else None,
                'completed': True,
                'current': obj.status == 'PENDING'
            },
            {
                'key': 'CONFIRMED',
                'title': 'Order Confirmed',
                'description': 'Gear verified in warehouse inventory.',
                'timestamp': obj.updated_at.isoformat() if obj.status in ['CONFIRMED', 'PROCESSING', 'SHIPPED', 'OUT_FOR_DELIVERY', 'DELIVERED'] else None,
                'completed': obj.status in ['CONFIRMED', 'PROCESSING', 'SHIPPED', 'OUT_FOR_DELIVERY', 'DELIVERED'],
                'current': obj.status in ['CONFIRMED', 'PROCESSING']
            },
            {
                'key': 'SHIPPED',
                'title': 'Dispatched / In Transit',
                'description': f"Dispatched via {meta.get('carrier', 'Courier')}." if meta.get('carrier') else 'Handed over to carrier.',
                'timestamp': obj.updated_at.isoformat() if obj.status in ['SHIPPED', 'OUT_FOR_DELIVERY', 'DELIVERED'] else None,
                'completed': obj.status in ['SHIPPED', 'OUT_FOR_DELIVERY', 'DELIVERED'],
                'current': obj.status == 'SHIPPED'
            },
            {
                'key': 'OUT_FOR_DELIVERY',
                'title': 'Ready for Pickup / Out for Delivery',
                'description': 'Ready at Turf desk or out with delivery courier.',
                'timestamp': obj.updated_at.isoformat() if obj.status in ['OUT_FOR_DELIVERY', 'DELIVERED'] else None,
                'completed': obj.status in ['OUT_FOR_DELIVERY', 'DELIVERED'],
                'current': obj.status == 'OUT_FOR_DELIVERY'
            },
            {
                'key': 'DELIVERED',
                'title': 'Delivered / Completed',
                'description': 'Package handed over to customer.',
                'timestamp': obj.updated_at.isoformat() if obj.status == 'DELIVERED' else None,
                'completed': obj.status == 'DELIVERED',
                'current': obj.status == 'DELIVERED'
            }
        ]
        if obj.status == 'CANCELLED':
            steps.append({
                'key': 'CANCELLED',
                'title': 'Order Cancelled',
                'description': meta.get('notes') or 'Order has been cancelled.',
                'timestamp': obj.updated_at.isoformat() if obj.updated_at else None,
                'completed': True,
                'current': True
            })
        return steps


