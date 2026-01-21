from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from .models import Patrol
from .serializers import PatrolSerializer
from apps.drones.models import Drone

class PatrolViewSet(viewsets.ModelViewSet):
    queryset = Patrol.objects.all()
    serializer_class = PatrolSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        # Ordinary officers only see their own patrols
        if user.role == 'officer':
            return Patrol.objects.filter(officer=user)
        return Patrol.objects.all()

    @action(detail=False, methods=['post'], url_path='start')
    def start_patrol(self, request):
        """
        Start a new patrol for the authenticated officer.
        Requires 'drone_id' in body.
        Example: {"drone_id": "DR-123", "config": {"speed_limit": 80}}
        """
        user = request.user
        drone_id = request.data.get('drone_id')
        config = request.data.get('config', {})
        
        if not drone_id:
            return Response({"error": "drone_id is required"}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            drone = Drone.objects.get(drone_id=drone_id)
        except Drone.DoesNotExist:
            return Response({"error": "Drone not found"}, status=status.HTTP_404_NOT_FOUND)
            
        # Check if drone is already in an active patrol
        active_patrol = Patrol.objects.filter(drone=drone, status='ACTIVE').first()
        if active_patrol:
            return Response({
                "error": f"Drone is already on active patrol: {active_patrol.id}"
            }, status=status.HTTP_409_CONFLICT)
            
        patrol = Patrol.objects.create(
            officer=user,
            drone=drone,
            patrol_config=config,
            status='ACTIVE'
        )
    
        
        return Response(PatrolSerializer(patrol).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='end')
    def end_patrol(self, request, pk=None):
        """
        End an active patrol.
        """
        patrol = self.get_object()
        
        if patrol.status != 'ACTIVE':
            return Response({"error": "Patrol is not active"}, status=status.HTTP_400_BAD_REQUEST)
            
        patrol.status = 'COMPLETED'
        patrol.end_time = timezone.now()
        patrol.save()
        
        return Response(PatrolSerializer(patrol).data)
