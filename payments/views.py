from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.conf import settings
from bookings.models import Booking
from payments.models import Payment
import uuid

try:
    import razorpay
    RAZORPAY_AVAILABLE = True
except ImportError:
    RAZORPAY_AVAILABLE = False

class PaymentViewSet(viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated]
    
    def get_razorpay_client(self):
        if RAZORPAY_AVAILABLE and hasattr(settings, 'RAZORPAY_KEY_ID'):
            return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        return None

    @action(detail=False, methods=['post'])
    def create_order(self, request):
        """
        Creates a Razorpay order for a booking or shop purchase.
        """
        booking_id = request.data.get('booking_id')
        amount = request.data.get('amount')
        
        if not amount:
            return Response({'error': 'Amount is required'}, status=status.HTTP_400_BAD_REQUEST)

        # Convert to paise
        amount_in_paise = int(float(amount) * 100)
        
        client = self.get_razorpay_client()
        if client:
            try:
                # Create Order on Razorpay
                data = {
                    "amount": amount_in_paise,
                    "currency": "INR",
                    "receipt": f"receipt_{uuid.uuid4().hex[:10]}",
                }
                payment = client.order.create(data=data)
                order_id = payment['id']
            except Exception as e:
                return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            # Fallback mock for local testing without keys
            order_id = f"order_{uuid.uuid4().hex[:14]}"
            
        # Create local payment record
        Payment.objects.create(
            booking_id=booking_id if booking_id else None,
            amount=amount,
            provider='razorpay',
            provider_payment_id=order_id,
            status='PENDING'
        )

        return Response({
            'order_id': order_id,
            'amount': amount_in_paise,
            'currency': 'INR',
            'key': getattr(settings, 'RAZORPAY_KEY_ID', 'rzp_test_mock_key')
        })

    @action(detail=False, methods=['post'])
    def verify(self, request):
        """
        Verifies the Razorpay signature after frontend payment success.
        """
        razorpay_payment_id = request.data.get('razorpay_payment_id')
        razorpay_order_id = request.data.get('razorpay_order_id')
        razorpay_signature = request.data.get('razorpay_signature')
        
        payment = Payment.objects.filter(provider_payment_id=razorpay_order_id).first()
        if not payment:
            return Response({'error': 'Payment record not found'}, status=status.HTTP_404_NOT_FOUND)
            
        client = self.get_razorpay_client()
        if client:
            try:
                params_dict = {
                    'razorpay_order_id': razorpay_order_id,
                    'razorpay_payment_id': razorpay_payment_id,
                    'razorpay_signature': razorpay_signature
                }
                client.utility.verify_payment_signature(params_dict)
                payment.status = 'SUCCESS'
                payment.save()
            except Exception as e:
                payment.status = 'FAILED'
                payment.save()
                return Response({'error': 'Signature verification failed'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            # Mock success for testing
            payment.status = 'SUCCESS'
            payment.save()

        # If booking, confirm the booking
        if payment.booking:
            payment.booking.status = 'CONFIRMED'
            payment.booking.save()
            
        return Response({'status': 'SUCCESS'})
