from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from .models import Patrol
from .serializers import PatrolSerializer
from apps.drones.models import Drone

from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from apps.core.pagination import StandardResultsSetPagination

class PatrolViewSet(viewsets.ModelViewSet):
    queryset = Patrol.objects.all().order_by('-start_time')
    serializer_class = PatrolSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'drone__drone_id', 'officer__email']
    search_fields = ['officer__username', 'drone__drone_id']
    ordering_fields = ['start_time', 'end_time']
    
    def get_queryset(self):
        user = self.request.user
        
        # Handle schema generation and unauthenticated users
        if not user or not user.is_authenticated:
            return Patrol.objects.none()
            
        # Admins (staff) see all patrols, others only see their own
        if user.is_staff or getattr(user, 'role', None) == 'admin':
            return Patrol.objects.all().order_by('-start_time')
            
        return Patrol.objects.filter(officer=user).order_by('-start_time')

    @action(detail=False, methods=['post'], url_path='start')
    def start_patrol(self, request):
        """
        Start a new patrol.
        If user is admin, they can specify 'officer' (UUID).
        Otherwise, defaults to the authenticated user.
        Example: {"drone_id": "DR-123", "officer": "uuid-here", "config": {}}
        """
        user = request.user
        drone_id = request.data.get('drone_id')
        officer_id = request.data.get('officer')
        config = request.data.get('config', {})
        
        if not drone_id:
            return Response({"error": "drone_id is required"}, status=status.HTTP_400_BAD_REQUEST)
            
        # Determine the officer for the patrol
        patrol_officer = user
        if officer_id and (user.is_staff or getattr(user, 'role', None) == 'admin'):
            from apps.users.models import User
            try:
                patrol_officer = User.objects.get(id=officer_id)
            except (User.DoesNotExist, ValueError):
                return Response({"error": "Specified officer not found"}, status=status.HTTP_404_NOT_FOUND)

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
            officer=patrol_officer,
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
