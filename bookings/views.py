from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Booking
from .serializers import BookingSerializer, CreateHoldSerializer
from .services import BookingService

class BookingViewSet(viewsets.ModelViewSet):
    serializer_class = BookingSerializer

    def get_queryset(self):
        queryset = Booking.objects.all().order_by('-start_at')
        
        # Player filtering
        if self.request.query_params.get('player_me') == 'true' and self.request.user.is_authenticated:
            queryset = queryset.filter(user=self.request.user)
            
        # Manager filtering
        if self.request.query_params.get('manager_me') == 'true' and self.request.user.is_authenticated:
            queryset = queryset.filter(court__turf__owner=self.request.user)
            
        return queryset

    @action(detail=False, methods=['post'])
    def hold(self, request):
        serializer = CreateHoldSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        
        try:
            booking = BookingService.create_hold(
                user=request.user,
                court_id=data['court_id'],
                sport_id=data['sport_id'],
                start_at=data['start_at'],
                end_at=data['end_at']
            )
            return Response(BookingSerializer(booking).data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
