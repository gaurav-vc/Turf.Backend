from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import LiveScore
from .serializers import LiveScoreSerializer
import datetime

class LiveScoreViewSet(viewsets.ModelViewSet):
    queryset = LiveScore.objects.all()
    serializer_class = LiveScoreSerializer
    
    # Let anyone view live scores, but only authenticated users (umpires) can edit
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        qs = LiveScore.objects.filter(match__status__in=['SCHEDULED', 'ONGOING'])
        if self.request.query_params.get('umpire_me') == 'true' and self.request.user.is_authenticated:
            qs = qs.filter(match__tournament__organizer=self.request.user)
        return qs

    @action(detail=True, methods=['post'])
    def increment(self, request, pk=None):
        live_score = self.get_object()
        team = request.data.get('team')
        points = int(request.data.get('points', 1))
        event = request.data.get('event', f"Scored {points} points")
        
        if team == '1':
            live_score.team1_score += points
        elif team == '2':
            live_score.team2_score += points
        else:
            return Response({'error': 'Invalid team. Must be "1" or "2"'}, status=status.HTTP_400_BAD_REQUEST)
            
        # Log the event
        log_entry = {
            "time": datetime.datetime.now().strftime("%H:%M:%S"),
            "event": f"Team {team}: {event}"
        }
        live_score.event_log.append(log_entry)
        live_score.save()
        
        return Response(self.get_serializer(live_score).data)

    @action(detail=True, methods=['post'])
    def toggle_live(self, request, pk=None):
        live_score = self.get_object()
        live_score.is_live = not live_score.is_live
        live_score.save()
        return Response({'status': 'live status toggled', 'is_live': live_score.is_live})

    @action(detail=False, methods=['get'])
    def available_matches(self, request):
        from sports.models import Match
        from sports.serializers import MatchSerializer
        # Matches that are not completed, and don't already have an active LiveScore
        matches = Match.objects.filter(
            status__in=['SCHEDULED', 'ONGOING']
        ).exclude(
            live_score__is_live=True
        ).select_related('tournament', 'team1', 'team2')
        
        if request.user.is_authenticated:
            matches = matches.filter(tournament__organizer=request.user)
        else:
            matches = matches.none()
        
        serializer = MatchSerializer(matches, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def start_scoring(self, request):
        from sports.models import Match
        match_id = request.data.get('match_id')
        if not match_id:
            return Response({'error': 'match_id is required'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            match = Match.objects.get(id=match_id)
        except Match.DoesNotExist:
            return Response({'error': 'Match not found'}, status=status.HTTP_404_NOT_FOUND)
            
        # Get or create livescore
        live_score, created = LiveScore.objects.get_or_create(match=match)
        live_score.is_live = True
        live_score.save()
        
        # Update match status
        match.status = 'ONGOING'
        match.save()
        
        return Response(self.get_serializer(live_score).data)

    @action(detail=True, methods=['post'])
    def finish_scoring(self, request, pk=None):
        try:
            live_score = self.get_object()
            match = live_score.match
            
            # Determine winner based on score
            if live_score.team1_score > live_score.team2_score:
                match.winner = match.team1
            elif live_score.team2_score > live_score.team1_score:
                match.winner = match.team2
            
            # Save match score (if you have fields for it)
            live_score.is_live = False
            live_score.save()
            
            match.status = 'COMPLETED'
            match.save()
            
            # Delete the LiveScore object so it vanishes from the UI completely
            live_score.delete()
            
            return Response({'status': 'Match finished successfully'})
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print("ERROR IN FINISH SCORING:", error_details)
            return Response({'error': str(e), 'details': error_details}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
