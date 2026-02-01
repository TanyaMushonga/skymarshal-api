from rest_framework import viewsets, permissions
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from apps.core.pagination import StandardResultsSetPagination
from .models import Detection
from .serializers import DetectionSerializer

class DetectionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Detection.objects.all().order_by('-timestamp')
    serializer_class = DetectionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['vehicle_type', 'drone__drone_id', 'patrol', 'track_id']
    search_fields = ['license_plate', 'track_id']
    ordering_fields = ['timestamp', 'speed']
