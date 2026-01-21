from rest_framework import viewsets, status, filters
from apps.core.pagination import StandardResultsSetPagination
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from ..models import StreamSession
from ..serializers import StreamSessionSerializer

class StreamSessionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing stream sessions (read-only)
    """
    
    queryset = StreamSession.objects.select_related(
        'stream', 
        'stream__drone'
    ).all()
    serializer_class = StreamSessionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['stream', 'stream__drone']
    ordering_fields = ['start_time', 'end_time', 'frames_processed']
    ordering = ['-start_time']
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['stream__stream_url', 'stream__drone__drone_id']
    
    def get_queryset(self):
        """
        Filter by date range if provided
        """
        queryset = super().get_queryset()
        
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(start_time__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(start_time__date__lte=end_date)
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """
        Get all currently active sessions
        GET /api/v1/sessions/active/
        """
        active_sessions = self.get_queryset().filter(end_time__isnull=True)
        serializer = self.get_serializer(active_sessions, many=True)
        
        return Response({
            'count': active_sessions.count(),
            'results': serializer.data
        }, status=status.HTTP_200_OK)
