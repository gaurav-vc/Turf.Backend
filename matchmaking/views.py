from django.db import models
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import MatchmakingLobby, LobbyRequest
from .serializers import MatchmakingLobbySerializer, LobbyRequestSerializer

class MatchmakingLobbyViewSet(viewsets.ModelViewSet):
    queryset = MatchmakingLobby.objects.filter(is_active=True).order_by('date_time')
    serializer_class = MatchmakingLobbySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        qs = MatchmakingLobby.objects.filter(is_active=True).order_by('date_time')
        search = self.request.query_params.get('search', None)
        sport = self.request.query_params.get('sport', None)
        skill_level = self.request.query_params.get('skill_level', None)
        
        if search:
            qs = qs.filter(
                models.Q(title__icontains=search) | 
                models.Q(description__icontains=search) |
                models.Q(turf__name__icontains=search)
            )
        if sport:
            qs = qs.filter(sport__slug=sport)
        if skill_level:
            qs = qs.filter(skill_level=skill_level)
            
        return qs

    def perform_create(self, serializer):
        serializer.save(host=self.request.user)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def join(self, request, pk=None):
        lobby = self.get_object()
        
        if lobby.host == request.user:
            return Response({'error': 'You cannot request to join your own lobby.'}, status=status.HTTP_400_BAD_REQUEST)
            
        if LobbyRequest.objects.filter(lobby=lobby, player=request.user).exists():
            return Response({'error': 'You have already requested to join this lobby.'}, status=status.HTTP_400_BAD_REQUEST)
            
        message = request.data.get('message', '')
        LobbyRequest.objects.create(lobby=lobby, player=request.user, message=message)
        
        return Response({'status': 'Join request sent.'})

class LobbyRequestViewSet(viewsets.ModelViewSet):
    serializer_class = LobbyRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Users see requests for lobbies they host, and requests they made
        return LobbyRequest.objects.filter(models.Q(lobby__host=self.request.user) | models.Q(player=self.request.user))
    
    def perform_create(self, serializer):
        serializer.save(player=self.request.user)

    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        req = self.get_object()
        if req.lobby.host != request.user:
            return Response({'error': 'Not authorized.'}, status=status.HTTP_403_FORBIDDEN)
        
        req.status = 'ACCEPTED'
        req.save()
        return Response({'status': 'Request accepted.'})

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        req = self.get_object()
        if req.lobby.host != request.user:
            return Response({'error': 'Not authorized.'}, status=status.HTTP_403_FORBIDDEN)
        
        req.status = 'REJECTED'
        req.save()
        return Response({'status': 'Request rejected.'})
