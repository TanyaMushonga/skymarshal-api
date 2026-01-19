from rest_framework import viewsets
from apps.core.permissions import IsAdminOrReadOnly
from ..models import DroneStatus
from ..serializers import DroneStatusSerializer

class DroneStatusViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for drone status monitoring.
    - Read operations: authenticated users
    - Write operations: Disabled (Drones update their own status via DroneViewSet)
    """
    queryset = DroneStatus.objects.select_related('drone')
    serializer_class = DroneStatusSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        """Filter status based on user permissions"""
        queryset = super().get_queryset()

        # If not admin, only show status for accessible drones
        user = self.request.user
        if getattr(user, 'role', None) != 'admin' and not user.is_staff:
            queryset = queryset.filter(
                drone__is_active=True,
                drone__assigned_officer__in=[user, None]
            )

        return queryset
