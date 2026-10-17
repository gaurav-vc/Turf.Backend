from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from turfs.models import Turf
from sports.models import Team, Tournament

class GlobalSearchView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = request.query_params.get('q', '').strip()
        if not query:
            return Response([])

        results = []
        
        # Search Turfs
        turfs = Turf.objects.filter(name__icontains=query, is_active=True)[:5]
        for turf in turfs:
            results.append({
                'id': turf.id,
                'type': 'TURF',
                'title': turf.name,
                'subtitle': turf.location,
                'link': '/explore'
            })

        # Search Teams
        teams = Team.objects.filter(name__icontains=query, user=request.user)[:5]
        for team in teams:
            results.append({
                'id': team.id,
                'type': 'TEAM',
                'title': team.name,
                'subtitle': f"{team.sport.name} Team",
                'link': '/teams'
            })

        # Search Tournaments
        tournaments = Tournament.objects.filter(
            Q(name__icontains=query) & (Q(privacy='PUBLIC') | Q(organizer=request.user))
        ).distinct()[:5]
        
        for tour in tournaments:
            results.append({
                'id': tour.id,
                'type': 'TOURNAMENT',
                'title': tour.name,
                'subtitle': tour.get_tournament_type_display(),
                'link': '/tournaments'
            })

        return Response(results)
