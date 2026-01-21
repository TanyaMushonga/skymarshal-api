from rest_framework import viewsets, permissions
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from apps.core.pagination import StandardResultsSetPagination
from .models import Violation
from .serializers import ViolationSerializer

class ViolationViewSet(viewsets.ReadOnlyModelViewSet):
    # Violations purely created by signals/system usually, but admins might edit.
    # ReadOnly for now is safer until requirements clarify.
    queryset = Violation.objects.all().order_by('-created_at')
    serializer_class = ViolationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'violation_type', 'drone__drone_id', 'patrol']
    search_fields = ['license_plate', 'citation_number']
    ordering_fields = ['created_at', 'fine_amount']
