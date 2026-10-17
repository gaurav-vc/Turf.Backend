import json
from decimal import Decimal
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db import models
from django.db.models import Q
from .models import Product, ShopOrder, OrderItem, ProductReview
from .serializers import ProductSerializer, ShopOrderSerializer, ProductReviewSerializer

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all().order_by('-created_at')
    serializer_class = ProductSerializer

    def get_permissions(self):
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        qs = super().get_queryset()
        category = self.request.query_params.get('category')
        sport = self.request.query_params.get('sport')
        search = self.request.query_params.get('search')
        in_stock = self.request.query_params.get('in_stock')

        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(description__icontains=search))
        if category and category.lower() != 'all':
            qs = qs.filter(Q(description__icontains=category) | Q(name__icontains=category))
        if sport and sport.lower() != 'all':
            qs = qs.filter(Q(description__icontains=sport) | Q(name__icontains=sport))
        if in_stock in ['true', 'True', '1']:
            qs = qs.filter(in_stock=True)

        return qs

    def _sync_product_metadata(self, product, data):
        """
        Dynamically extracts and updates rich e-commerce metadata
        into Product.description as structured JSON without schema alterations.
        Rating and review counts are strictly calculated dynamically from ProductReview models.
        """
        meta = {}
        if product.description and product.description.strip().startswith('{'):
            try:
                meta = json.loads(product.description)
            except Exception:
                meta = {}

        # Remove any legacy manual rating/reviews_count keys
        meta.pop('rating', None)
        meta.pop('reviews_count', None)

        if 'category' in data:
            meta['category'] = str(data['category']).strip() if data['category'] is not None else ""
        if 'sport' in data:
            meta['sport'] = str(data['sport']).strip() if data['sport'] is not None else ""
        if 'badge' in data:
            meta['badge'] = str(data['badge']).strip() if data['badge'] is not None else ""
        if 'original_price' in data:
            if data['original_price'] not in [None, '']:
                try:
                    meta['original_price'] = float(data['original_price'])
                except (ValueError, TypeError):
                    meta['original_price'] = None
            else:
                meta['original_price'] = None
        if 'is_customizable' in data:
            val = data['is_customizable']
            meta['is_customizable'] = val in [True, 'true', 'True', '1', 1]

        
        # Description text
        if 'description_text' in data:
            meta['description_text'] = str(data['description_text']).strip() if data['description_text'] is not None else ""
        elif 'description' in data and data['description'] and not str(data['description']).strip().startswith('{'):
            meta['description_text'] = str(data['description']).strip()

        # Sizes (can be JSON array or comma-separated string)
        if 'sizes' in data:
            sizes_val = data['sizes']
            if isinstance(sizes_val, str):
                if not sizes_val.strip():
                    meta['sizes'] = []
                else:
                    try:
                        parsed = json.loads(sizes_val)
                        if isinstance(parsed, list):
                            meta['sizes'] = [str(s).strip() for s in parsed if str(s).strip()]
                        else:
                            meta['sizes'] = [s.strip() for s in sizes_val.split(',') if s.strip()]
                    except Exception:
                        meta['sizes'] = [s.strip() for s in sizes_val.split(',') if s.strip()]
            elif isinstance(sizes_val, list):
                meta['sizes'] = [str(s).strip() for s in sizes_val if str(s).strip()]
            else:
                meta['sizes'] = []

        # Features / Highlights (can be JSON array, multiline string, or comma-separated)
        if 'features' in data:
            feat_val = data['features']
            if isinstance(feat_val, str):
                if not feat_val.strip():
                    meta['features'] = []
                else:
                    try:
                        parsed = json.loads(feat_val)
                        if isinstance(parsed, list):
                            meta['features'] = [str(f).strip() for f in parsed if str(f).strip()]
                        else:
                            lines = [f.strip() for f in feat_val.replace('\r', '').split('\n') if f.strip()]
                            if not lines:
                                lines = [f.strip() for f in feat_val.split(',') if f.strip()]
                            meta['features'] = lines
                    except Exception:
                        lines = [f.strip() for f in feat_val.replace('\r', '').split('\n') if f.strip()]
                        if not lines:
                            lines = [f.strip() for f in feat_val.split(',') if f.strip()]
                        meta['features'] = lines
            elif isinstance(feat_val, list):
                meta['features'] = [str(f).strip() for f in feat_val if str(f).strip()]
            else:
                meta['features'] = []

        # Image URL (external/cloud)
        if 'image_url' in data:
            meta['image_url'] = str(data['image_url']).strip() if data['image_url'] else ""

        product.description = json.dumps(meta)
        product.save(update_fields=['description'])

    def perform_create(self, serializer):
        instance = serializer.save()
        self._sync_product_metadata(instance, self.request.data)

    def perform_update(self, serializer):
        instance = serializer.save()
        self._sync_product_metadata(instance, self.request.data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            ProductSerializer(serializer.instance, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
            headers=headers
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(
            ProductSerializer(serializer.instance, context={'request': request}).data
        )

    @action(detail=True, methods=['get'])
    def reviews(self, request, pk=None):
        """
        Returns real-time reviews list, average rating, star breakdown,
        and purchase verification status for the current user.
        """
        product = self.get_object()
        reviews_qs = product.reviews.filter(is_active=True).order_by('-created_at')
        count = reviews_qs.count()
        avg = round(float(reviews_qs.aggregate(models.Avg('rating'))['rating__avg']), 1) if count > 0 else None

        breakdown = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
        for r in reviews_qs:
            if 1 <= r.rating <= 5:
                breakdown[r.rating] = breakdown.get(r.rating, 0) + 1

        has_purchased = False
        user_review = None
        if request.user and request.user.is_authenticated:
            if getattr(request.user, 'user_type', '') in ['ADMIN', 'MANAGER'] or getattr(request.user, 'is_staff', False):
                has_purchased = True
            else:
                has_purchased = ShopOrder.objects.filter(user=request.user, items__product=product).exists()

            my_rev = reviews_qs.filter(user=request.user).first()
            if my_rev:
                user_review = ProductReviewSerializer(my_rev).data

        return Response({
            'product_id': product.id,
            'rating': avg,
            'reviews_count': count,
            'breakdown': breakdown,
            'has_purchased': has_purchased,
            'user_review': user_review,
            'reviews': ProductReviewSerializer(reviews_qs, many=True).data
        })

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def rate(self, request, pk=None):
        """
        Allows an employee/user who purchased the product to rate (1 to 5 stars)
        and provide review feedback. Real-time rating dynamically recalculated.
        """
        product = self.get_object()
        rating_val = request.data.get('rating')
        comment_val = str(request.data.get('comment', '')).strip()

        if rating_val is None:
            return Response({'error': 'Rating (1-5) is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            rating_num = int(rating_val)
            if rating_num < 1 or rating_num > 5:
                return Response({'error': 'Rating must be an integer between 1 and 5.'}, status=status.HTTP_400_BAD_REQUEST)
        except (ValueError, TypeError):
            return Response({'error': 'Rating must be a valid integer between 1 and 5.'}, status=status.HTTP_400_BAD_REQUEST)

        # Verification check: has the employee/user purchased the product?
        is_admin_or_mgr = getattr(request.user, 'user_type', '') in ['ADMIN', 'MANAGER'] or getattr(request.user, 'is_staff', False)
        has_purchased = ShopOrder.objects.filter(user=request.user, items__product=product).exists()

        if not has_purchased and not is_admin_or_mgr:
            return Response({
                'error': 'Only verified buyers can review this product. Please purchase the product to submit your review.'
            }, status=status.HTTP_403_FORBIDDEN)

        # Find latest order if applicable
        order = ShopOrder.objects.filter(user=request.user, items__product=product).order_by('-created_at').first()

        review, created = ProductReview.objects.update_or_create(
            product=product,
            user=request.user,
            defaults={
                'rating': rating_num,
                'comment': comment_val,
                'order': order,
                'verified_purchase': True,
                'is_active': True,
            }
        )

        # Real-time recalculated stats
        active_reviews = product.reviews.filter(is_active=True)
        count = active_reviews.count()
        avg = round(float(active_reviews.aggregate(models.Avg('rating'))['rating__avg']), 1) if count > 0 else None

        return Response({
            'message': 'Review submitted successfully!',
            'created': created,
            'rating': avg,
            'reviews_count': count,
            'review': ProductReviewSerializer(review).data,
            'product': ProductSerializer(product, context={'request': request}).data
        }, status=status.HTTP_200_OK if not created else status.HTTP_201_CREATED)

    @action(detail=True, methods=['delete'], permission_classes=[permissions.IsAuthenticated])
    def delete_review(self, request, pk=None):
        product = self.get_object()
        review = ProductReview.objects.filter(product=product, user=request.user).first()
        if not review:
            return Response({'error': 'Review not found.'}, status=status.HTTP_404_NOT_FOUND)

        review.delete()
        active_reviews = product.reviews.filter(is_active=True)
        count = active_reviews.count()
        avg = round(float(active_reviews.aggregate(models.Avg('rating'))['rating__avg']), 1) if count > 0 else None

        return Response({
            'message': 'Review removed successfully.',
            'rating': avg,
            'reviews_count': count
        })

    @action(detail=False, methods=['post', 'get'])
    def seed_initial(self, request):
        """
        Dynamically seeds the database with authentic sports merchandise if needed.
        Safe and idempotent.
        """
        from .models import Product
        from seed_shop import INITIAL_PRODUCTS

        created = 0
        updated = 0
        for p_data in INITIAL_PRODUCTS:
            meta = dict(p_data.get('metadata', {}))
            # Strip legacy manual rating & reviews_count
            meta.pop('rating', None)
            meta.pop('reviews_count', None)
            desc_json = json.dumps(meta)
            prod, was_created = Product.objects.get_or_create(
                name=p_data['name'],
                defaults={
                    'base_price': p_data['base_price'],
                    'in_stock': p_data['in_stock'],
                    'description': desc_json
                }
            )
            if was_created:
                created += 1
            else:
                if not prod.description or not prod.description.strip().startswith('{'):
                    prod.description = desc_json
                    prod.base_price = p_data['base_price']
                    prod.save()
                    updated += 1

        all_products = Product.objects.all().order_by('-created_at')
        return Response({
            'message': f'Seeded {created} new products, updated {updated}.',
            'total_products': all_products.count(),
            'products': ProductSerializer(all_products, many=True, context={'request': request}).data
        })


from rest_framework.pagination import PageNumberPagination
from django.utils import timezone

class ShopOrderPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response({
            'count': self.page.paginator.count,
            'total_pages': self.page.paginator.num_pages,
            'current_page': self.page.number,
            'page_size': self.get_page_size(self.request),
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data
        })

class ShopOrderViewSet(viewsets.ModelViewSet):
    serializer_class = ShopOrderSerializer
    pagination_class = ShopOrderPagination
    permission_classes = [permissions.IsAuthenticated]

    def _is_admin_or_mgr(self):
        user = self.request.user
        return getattr(user, 'user_type', '') in ['ADMIN', 'MANAGER'] or getattr(user, 'is_staff', False) or getattr(user, 'is_superuser', False)

    def get_queryset(self):
        user = self.request.user
        if self._is_admin_or_mgr():
            qs = ShopOrder.objects.all()
        else:
            qs = ShopOrder.objects.filter(user=user)

        qs = qs.select_related('user').prefetch_related('items__product')

        # Filters
        status_param = self.request.query_params.get('status')
        if status_param and status_param.upper() != 'ALL':
            qs = qs.filter(status__iexact=status_param.strip())

        search = self.request.query_params.get('search')
        if search:
            search = search.strip()
            qs = qs.filter(
                Q(id__icontains=search) |
                Q(user__full_name__icontains=search) |
                Q(user__email__icontains=search) |
                Q(user__phone__icontains=search) |
                Q(delivery_address__icontains=search) |
                Q(items__product__name__icontains=search)
            ).distinct()

        delivery_type = self.request.query_params.get('delivery_type')
        if delivery_type and delivery_type.upper() != 'ALL':
            qs = qs.filter(delivery_address__icontains=delivery_type.strip())

        date_from = self.request.query_params.get('date_from')
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)

        date_to = self.request.query_params.get('date_to')
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)

        min_amount = self.request.query_params.get('min_amount')
        if min_amount:
            try:
                qs = qs.filter(total_amount__gte=Decimal(min_amount))
            except Exception:
                pass

        max_amount = self.request.query_params.get('max_amount')
        if max_amount:
            try:
                qs = qs.filter(total_amount__lte=Decimal(max_amount))
            except Exception:
                pass

        ordering = self.request.query_params.get('ordering', '-created_at')
        allowed_orderings = ['-created_at', 'created_at', '-total_amount', 'total_amount', 'status', '-status']
        if ordering in allowed_orderings:
            qs = qs.order_by(ordering)
        else:
            qs = qs.order_by('-created_at')

        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Returns dynamic summary statistics for orders dashboard
        """
        if self._is_admin_or_mgr():
            qs = ShopOrder.objects.all()
        else:
            qs = ShopOrder.objects.filter(user=request.user)

        total_orders = qs.count()
        pending_orders = qs.filter(status='PENDING').count()
        confirmed_orders = qs.filter(status__in=['CONFIRMED', 'PROCESSING']).count()
        shipped_orders = qs.filter(status__in=['SHIPPED', 'OUT_FOR_DELIVERY']).count()
        delivered_orders = qs.filter(status='DELIVERED').count()
        cancelled_orders = qs.filter(status='CANCELLED').count()

        revenue_qs = qs.exclude(status='CANCELLED')
        total_rev = revenue_qs.aggregate(models.Sum('total_amount'))['total_amount__sum'] or Decimal('0.00')

        today_count = qs.filter(created_at__date=timezone.now().date()).count()
        pickup_count = qs.filter(delivery_address__icontains='VENUE_PICKUP').count()
        courier_count = qs.filter(delivery_address__icontains='HOME_DELIVERY').count()

        return Response({
            'total_orders': total_orders,
            'pending_orders': pending_orders,
            'confirmed_orders': confirmed_orders,
            'shipped_orders': shipped_orders,
            'delivered_orders': delivered_orders,
            'cancelled_orders': cancelled_orders,
            'total_revenue': float(total_rev),
            'today_orders': today_count,
            'pickup_count': pickup_count,
            'courier_count': courier_count,
        })

    @action(detail=True, methods=['patch', 'post'], permission_classes=[permissions.IsAuthenticated])
    def update_tracking(self, request, pk=None):
        """
        Admin action to update order status, tracking number, carrier, and notes.
        """
        if not self._is_admin_or_mgr():
            return Response({'error': 'Permission denied. Admins and managers only.'}, status=status.HTTP_403_FORBIDDEN)

        order = self.get_object()
        new_status = request.data.get('status')
        carrier = str(request.data.get('carrier', '')).strip()
        tracking_number = str(request.data.get('tracking_number', '')).strip()
        estimated_delivery = str(request.data.get('estimated_delivery', '')).strip()
        notes = str(request.data.get('notes', '')).strip()

        if new_status:
            order.status = new_status.upper().strip()

        # Update or enrich delivery metadata in delivery_address
        current_meta = {}
        raw = order.delivery_address or ""
        if raw.strip().startswith('{'):
            try:
                current_meta = json.loads(raw)
            except Exception:
                current_meta = {}
        else:
            del_type = 'VENUE_PICKUP'
            addr = raw
            if raw.startswith('['):
                end_idx = raw.find(']')
                if end_idx != -1:
                    del_type = raw[1:end_idx]
                    addr = raw[end_idx+1:].strip()
            current_meta = {
                'delivery_type': del_type,
                'address': addr
            }

        if carrier:
            current_meta['carrier'] = carrier
        if tracking_number:
            current_meta['tracking_number'] = tracking_number
        if estimated_delivery:
            current_meta['estimated_delivery'] = estimated_delivery
        if notes:
            current_meta['notes'] = notes

        order.delivery_address = json.dumps(current_meta)
        order.save()

        # Send notification to the user if Notification model exists
        try:
            from accounts.models import Notification
            short_id = str(order.id)[:8].upper()
            status_text = order.status.replace('_', ' ').title()
            msg = f"Your gear order #{short_id} is now {status_text}."
            if carrier and tracking_number:
                msg += f" Dispatched via {carrier} (Tracking: {tracking_number})."
            elif notes:
                msg += f" Note: {notes}"

            Notification.objects.create(
                user=order.user,
                title=f"Order Update: #{short_id}",
                message=msg,
                type='ORDER',
                link='/orders'
            )
        except Exception as e:
            pass

        return Response(ShopOrderSerializer(order, context={'request': request}).data)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def cancel_order(self, request, pk=None):
        """
        Allows customer to cancel pending order or admin to cancel.
        """
        order = self.get_object()
        is_admin = self._is_admin_or_mgr()
        
        if not is_admin and order.user != request.user:
            return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)

        if not is_admin and order.status != 'PENDING':
            return Response({'error': 'Only pending orders can be cancelled by customers.'}, status=status.HTTP_400_BAD_REQUEST)

        order.status = 'CANCELLED'
        order.save(update_fields=['status', 'updated_at'])

        try:
            from accounts.models import Notification
            Notification.objects.create(
                user=order.user,
                title=f"Order Cancelled: #{str(order.id)[:8].upper()}",
                message="Your order has been cancelled.",
                type='ORDER',
                link='/orders'
            )
        except Exception:
            pass

        return Response({
            'message': 'Order cancelled successfully.',
            'order': ShopOrderSerializer(order, context={'request': request}).data
        })

    @action(detail=False, methods=['post'])
    def checkout(self, request):
        items_data = request.data.get('items', [])
        if not items_data:
            return Response({'error': 'Cart is empty'}, status=status.HTTP_400_BAD_REQUEST)

        delivery_address = request.data.get('delivery_address', '')
        delivery_type = request.data.get('delivery_type', 'VENUE_PICKUP')

        # Calculate total
        total = Decimal('0.00')
        order_items = []
        for item in items_data:
            prod_id = item.get('product_id')
            qty = int(item.get('quantity', 1))
            try:
                product = Product.objects.get(id=prod_id)
            except Product.DoesNotExist:
                continue

            item_price = product.base_price * qty
            total += item_price
            order_items.append((product, item, qty))

        if not order_items:
            return Response({'error': 'No valid products in cart'}, status=status.HTTP_400_BAD_REQUEST)

        # Apply promo discount if passed
        promo = request.data.get('promo_code', '').upper()
        if promo == 'TURFPRO10':
            total = total * Decimal('0.90')
        elif promo == 'WELCOME50':
            total = max(Decimal('0.00'), total - Decimal('50.00'))

        # Add delivery fee if home delivery and subtotal < 1500
        if delivery_type == 'HOME_DELIVERY' and total < Decimal('1500.00'):
            total += Decimal('99.00')

        # Structured delivery notes
        deliv_meta = {
            'delivery_type': delivery_type,
            'address': delivery_address or ('Turf Venue Pickup Desk' if delivery_type == 'VENUE_PICKUP' else ''),
            'carrier': 'Turf Venue Desk' if delivery_type == 'VENUE_PICKUP' else 'Standard Courier',
            'tracking_number': '',
            'estimated_delivery': '',
            'notes': ''
        }

        order = ShopOrder.objects.create(
            user=request.user,
            total_amount=total,
            delivery_address=json.dumps(deliv_meta),
            status='PENDING'
        )
        deliv_meta['tracking_number'] = f"TRK-{str(order.id)[:8].upper()}"
        order.delivery_address = json.dumps(deliv_meta)
        order.save(update_fields=['delivery_address'])

        created_items_summary = []
        for prod, item, qty in order_items:
            OrderItem.objects.create(
                order=order,
                product=prod,
                quantity=qty,
                custom_name=item.get('custom_name', ''),
                custom_number=item.get('custom_number', ''),
                size=item.get('size', 'M')
            )
            created_items_summary.append({
                'product_id': str(prod.id),
                'name': prod.name,
                'quantity': qty,
                'base_price': float(prod.base_price),
                'image': ProductSerializer(prod, context={'request': request}).data.get('image_url') or ''
            })

        # Send order confirmation notification
        try:
            from accounts.models import Notification
            Notification.objects.create(
                user=request.user,
                title=f"Order Confirmed: #{str(order.id)[:8].upper()}",
                message=f"Thank you for your order of {len(order_items)} items (₹{total:,.2f}).",
                type='ORDER',
                link='/orders'
            )
        except Exception:
            pass

        return Response({
            'order_id': str(order.id),
            'total_amount': total,
            'items': created_items_summary
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post', 'get'])
    def seed_sample_orders(self, request):
        """
        Dynamically generates realistic sample orders across different users & statuses
        so pagination (10 records/page), filtering, and tracking can be thoroughly tested.
        """
        if not self._is_admin_or_mgr():
            return Response({'error': 'Admins only'}, status=status.HTTP_403_FORBIDDEN)

        products = list(Product.objects.all()[:8])
        if not products:
            return Response({'error': 'No products in database to create orders.'}, status=status.HTTP_400_BAD_REQUEST)

        users = list(request.user.__class__.objects.all()[:5])
        if not users:
            users = [request.user]

        sample_configs = [
            {'status': 'DELIVERED', 'carrier': 'BlueDart Express', 'type': 'HOME_DELIVERY', 'addr': '402, Green Park Avenue, Bandra West, Mumbai', 'notes': 'Delivered to resident'},
            {'status': 'SHIPPED', 'carrier': 'Delhivery', 'type': 'HOME_DELIVERY', 'addr': '12B, Sunset Residency, Koregaon Park, Pune', 'notes': 'In transit to Pune Hub'},
            {'status': 'CONFIRMED', 'carrier': 'Turf Venue Desk', 'type': 'VENUE_PICKUP', 'addr': 'TurfArena Counter #2, Main Turf', 'notes': 'Packed and awaiting match day pickup'},
            {'status': 'PENDING', 'carrier': 'Turf Venue Desk', 'type': 'VENUE_PICKUP', 'addr': 'Turf Arena Collection Counter', 'notes': 'Order placed, awaiting confirmation'},
            {'status': 'OUT_FOR_DELIVERY', 'carrier': 'Shadowfax', 'type': 'HOME_DELIVERY', 'addr': 'Flat 801, Prestige Heights, Indiranagar, Bengaluru', 'notes': 'Out for delivery today with courier agent'},
            {'status': 'DELIVERED', 'carrier': 'DTDC Courier', 'type': 'HOME_DELIVERY', 'addr': 'Sector 45, DLF Phase 4, Gurgaon', 'notes': 'Handed over to security desk'},
            {'status': 'CANCELLED', 'carrier': 'None', 'type': 'HOME_DELIVERY', 'addr': 'Plot 18, Road No. 36, Jubilee Hills, Hyderabad', 'notes': 'Customer requested cancellation'},
            {'status': 'CONFIRMED', 'carrier': 'BlueDart', 'type': 'HOME_DELIVERY', 'addr': 'Flat 5A, Silver Arch, Marine Drive, Mumbai', 'notes': 'Packaging jersey with custom print'},
            {'status': 'SHIPPED', 'carrier': 'Delhivery', 'type': 'HOME_DELIVERY', 'addr': 'B-304, Palm Springs, Viman Nagar, Pune', 'notes': 'Dispatched from central warehouse'},
            {'status': 'PENDING', 'carrier': 'Turf Venue Desk', 'type': 'VENUE_PICKUP', 'addr': 'Turf Arena Pickup Desk', 'notes': 'New order awaiting inventory check'},
            {'status': 'DELIVERED', 'carrier': 'Turf Venue Desk', 'type': 'VENUE_PICKUP', 'addr': 'Turf Arena Counter #1', 'notes': 'Picked up during football tournament'},
            {'status': 'SHIPPED', 'carrier': 'BlueDart Express', 'type': 'HOME_DELIVERY', 'addr': 'Block C, Salt Lake City, Sector 5, Kolkata', 'notes': 'Waybill tracking active'},
        ]

        created_count = 0
        for i, cfg in enumerate(sample_configs):
            target_user = users[i % len(users)]
            prod_sample = products[i % len(products)]
            qty = (i % 3) + 1
            tot = prod_sample.base_price * qty
            if cfg['type'] == 'HOME_DELIVERY':
                tot += Decimal('99.00')

            deliv_meta = {
                'delivery_type': cfg['type'],
                'address': cfg['addr'],
                'carrier': cfg['carrier'],
                'tracking_number': f"TRK-{100000 + i * 437}",
                'estimated_delivery': '2026-10-18',
                'notes': cfg['notes']
            }

            ord_obj = ShopOrder.objects.create(
                user=target_user,
                total_amount=tot,
                delivery_address=json.dumps(deliv_meta),
                status=cfg['status']
            )

            OrderItem.objects.create(
                order=ord_obj,
                product=prod_sample,
                quantity=qty,
                custom_name="PLAYER" if i % 2 == 0 else "",
                custom_number=str(7 + (i % 15)) if i % 2 == 0 else "",
                size='L' if i % 2 == 0 else 'M'
            )
            created_count += 1

        all_orders = ShopOrder.objects.all().order_by('-created_at')
        return Response({
            'message': f'Created {created_count} authentic sample orders.',
            'total_orders': all_orders.count()
        })




