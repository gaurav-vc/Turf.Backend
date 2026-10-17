from rest_framework import viewsets
from rest_framework.response import Response
from .models import Turf, Court, BlockedPeriod, PriceRule
from .serializers import TurfSerializer, CourtSerializer, BlockedPeriodSerializer, PriceRuleSerializer

from rest_framework.pagination import PageNumberPagination

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

class TurfViewSet(viewsets.ModelViewSet):
    serializer_class = TurfSerializer
    
    def get_queryset(self):
        queryset = Turf.objects.all().order_by('-created_at')
        
        # Dynamic filtering without hardcoding roles
        if self.request.query_params.get('owner_me') == 'true' and self.request.user.is_authenticated:
            queryset = queryset.filter(owner=self.request.user)
            
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        
        if request.query_params.get('paginate') == 'true':
            self.pagination_class = StandardResultsSetPagination
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)
                
        self.pagination_class = None
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

class CourtViewSet(viewsets.ModelViewSet):
    serializer_class = CourtSerializer

    def get_queryset(self):
        queryset = Court.objects.all().order_by('-created_at')
        
        # Dynamic filtering without hardcoding roles
        if self.request.query_params.get('owner_me') == 'true' and self.request.user.is_authenticated:
            queryset = queryset.filter(turf__owner=self.request.user)
            
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        
        if request.query_params.get('paginate') == 'true':
            self.pagination_class = StandardResultsSetPagination
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)
                
        self.pagination_class = None
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

class BlockedPeriodViewSet(viewsets.ModelViewSet):
    serializer_class = BlockedPeriodSerializer
    filterset_fields = ['court', 'court__turf']

    def get_queryset(self):
        queryset = BlockedPeriod.objects.all().order_by('-created_at')
        if self.request.query_params.get('owner_me') == 'true' and self.request.user.is_authenticated:
            queryset = queryset.filter(court__turf__owner=self.request.user)
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        
        if request.query_params.get('paginate') == 'true':
            self.pagination_class = StandardResultsSetPagination
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)
                
        self.pagination_class = None
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

class PriceRuleViewSet(viewsets.ModelViewSet):
    queryset = PriceRule.objects.all()
    serializer_class = PriceRuleSerializer
    filterset_fields = ['turf', 'court']
