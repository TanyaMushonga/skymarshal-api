from rest_framework import viewsets, permissions
from apps.core.permissions import IsAdminOrReadOnly
from ..models import GPSLocation
from ..serializers import (
    GPSLocationSerializer,
)


class GPSLocationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for GPS location data.
    - Read operations: authenticated users (filtered by permissions)
    - Write operations: admin only
    """
    queryset = GPSLocation.objects.select_related('drone').order_by('-timestamp')
    serializer_class = GPSLocationSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        """Filter locations based on user permissions"""
        queryset = super().get_queryset()

        # If not admin, only show locations for drones user has access to
        user = self.request.user
        if getattr(user, 'role', None) != 'admin' and not user.is_staff:
            queryset = queryset.filter(
                drone__is_active=True,
                drone__assigned_officer__in=[user, None]
            )

        return queryset

    def perform_create(self, serializer):
        """Ensure GPS location is created for accessible drones only"""
        drone = serializer.validated_data['drone']
        user = self.request.user
        if getattr(user, 'role', None) != 'admin' and not user.is_staff:
            # Non-admin users can only add locations for their assigned drones
            if drone.assigned_officer != user:
                raise permissions.PermissionDenied("Can only add locations for assigned drones")
        serializer.save()

