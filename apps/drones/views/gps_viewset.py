from rest_framework import viewsets
from apps.core.permissions import IsAdminOrReadOnly
from ..models import GPSLocation
from ..serializers import GPSLocationSerializer


class GPSLocationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing GPS location history.
    - Read operations: authenticated users (filtered by permissions)
    - Write operations: Disabled (Drones update their own location via DroneViewSet)
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
