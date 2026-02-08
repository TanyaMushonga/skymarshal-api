from rest_framework import viewsets, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum, Count

from .models import VehicleRegistration
from .serializers import VehicleRegistrationSerializer
from apps.detections.models import Detection
from apps.violations.models import Violation

class VehicleRegistrationViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing vehicle registrations and viewing history.
    Provides CRUD operations for vehicle records and a specific 'history' action
    that aggregates data from detections and violations.
    """
    queryset = VehicleRegistration.objects.all()
    serializer_class = VehicleRegistrationSerializer
    permission_classes = [permissions.IsAdminUser]  # Only admins can manage vehicles
    
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['license_plate', 'owner_name', 'make', 'model']
    ordering_fields = ['license_plate', 'status', 'created_at']
    ordering = ['-created_at']

    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        vehicle = self.get_object()
        plate = vehicle.license_plate
        
        # 1. Fetch Detections
        # Note: Detections have 'license_plate' field (denormalized or detected via OCR)
        detections = Detection.objects.filter(license_plate=plate).order_by('-timestamp')
        
        # 2. Fetch Violations (via Detections)
        # Violations are linked to Detection, so we query Violations where detection__license_plate=plate
        violations = Violation.objects.filter(detection__license_plate=plate).order_by('-created_at')
        
        # 3. Aggregates
        total_violations = violations.count()
        total_fines = violations.aggregate(total=Sum('fine_amount'))['total'] or 0.00
        
        # 4. Serialize (Basic inline serialization for report)
        detection_data = [{
            'id': d.id,
            'timestamp': d.timestamp,
            'speed': d.speed,
            'location': d.location.coords if d.location else None,
            'drone_id': d.drone.drone_id
        } for d in detections[:50]] # Limit to recent 50
        
        violation_data = [{
            'id': v.id,
            'type': v.violation_type,
            'status': v.status,
            'fine': v.fine_amount,
            'timestamp': v.created_at,
            'video_url': v.video_clip.url if v.video_clip else None
        } for v in violations]
        
        return Response({
            'vehicle': VehicleRegistrationSerializer(vehicle).data,
            'statistics': {
                'total_detections': detections.count(),
                'total_violations': total_violations,
                'total_fines_outstanding': total_fines, # Assuming all for now
            },
            'recent_detections': detection_data,
            'violations_history': violation_data
        })
