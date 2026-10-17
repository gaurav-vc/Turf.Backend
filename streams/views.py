from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import LiveStream
from .serializers import LiveStreamSerializer

class LiveStreamViewSet(viewsets.ModelViewSet):
    serializer_class = LiveStreamSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        if self.action in ['retrieve', 'update', 'partial_update', 'destroy', 'end_stream']:
            return LiveStream.objects.all()
        show_all = self.request.query_params.get('all') == 'true'
        if show_all:
            return LiveStream.objects.all().order_by('-created_at')
        return LiveStream.objects.filter(is_live=True).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(organizer=self.request.user, is_live=True)

    @action(detail=True, methods=['post'])
    def end_stream(self, request, pk=None):
        stream = self.get_object()
        # Allow stream organizer or staff/admin to end stream
        user = request.user
        if not user.is_authenticated:
            return Response({'error': 'Authentication required.'}, status=status.HTTP_401_UNAUTHORIZED)
        is_organizer = stream.organizer_id == user.id
        is_staff_or_admin = user.is_staff or getattr(user, 'user_type', '') in ['ADMIN', 'MANAGER']
        if not (is_organizer or is_staff_or_admin):
            return Response({'error': 'Only the stream host or turf admin can end this stream.'}, status=status.HTTP_403_FORBIDDEN)
        
        stream.is_live = False
        stream.save()
        return Response({'message': 'Live stream ended successfully.', 'stream': LiveStreamSerializer(stream).data})
