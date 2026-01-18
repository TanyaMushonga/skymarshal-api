from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Drone, Telemetry
from .serializers import DroneSerializer, TelemetrySerializer

class DroneViewSet(viewsets.ModelViewSet):
    queryset = Drone.objects.all()
    serializer_class = DroneSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'serial_number'

    @action(detail=True, methods=['post'], serializer_class=TelemetrySerializer)
    def telemetry(self, request, serial_number=None):
        """
        Custom endpoint to report telemetry for a specific drone.
        POST /api/v1/drones/{serial_number}/telemetry/
        """
        drone = self.get_object()
        serializer = TelemetrySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(drone=drone)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def history(self, request, serial_number=None):
        """
        Get telemetry history for a drone.
        """
        drone = self.get_object()
        telemetry = drone.telemetry_logs.all()[:100] # Limit to last 100 for now
        serializer = TelemetrySerializer(telemetry, many=True)
        return Response(serializer.data)

class TelemetryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only viewset for all telemetry (for admin/monitoring).
    """
    queryset = Telemetry.objects.all()
    serializer_class = TelemetrySerializer
    permission_classes = [permissions.IsAuthenticated]
