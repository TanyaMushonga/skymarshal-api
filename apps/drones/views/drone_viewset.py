from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from django.contrib.gis.geos import Point
from django.utils import timezone
from datetime import timedelta

from apps.core.permissions import IsAdmin
from apps.users.models import User
from ..models import Drone, DroneStatus, GPSLocation
from ..serializers import (
    DroneSerializer, DroneCreateSerializer, DroneStatusSerializer,
    GPSLocationSerializer, DroneStatusUpdateSerializer,
    DroneAssignSerializer, GPSLocationUpdateSerializer
)
from apps.core.permissions import IsDroneAuthenticated

from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from apps.core.pagination import StandardResultsSetPagination

class DroneViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing drones.
    """
    queryset = Drone.objects.prefetch_related(
        'status'
    )
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'drone_id'
    
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status__status', 'is_active', 'model']
    search_fields = ['name', 'drone_id', 'model']
    ordering_fields = ['created_at', 'updated_at']

    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'assign', 'activate', 'deactivate']:
            permission_classes = [IsAdmin]
        elif self.action in ['list', 'retrieve', 'status', 'history', 'location']:
            permission_classes = [permissions.IsAuthenticated]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]

    def get_serializer_class(self):
        if self.action == 'create':
            return DroneCreateSerializer
        if self.action == 'assign':
            return DroneAssignSerializer
        if self.action == 'location' and self.request.method == 'POST':
            return GPSLocationUpdateSerializer
        if self.action in ['status', 'update_status'] and self.request.method in ['PUT', 'PATCH']:
            return DroneStatusUpdateSerializer
        return DroneSerializer

    def get_queryset(self):
        """Filter queryset based on user permissions"""
        queryset = Drone.objects.prefetch_related(
            'status'
        )

        # If not admin, only show active drones assigned to user or unassigned
        # Note: Depending on requirements, maybe officers should see all drones?
        # Assuming officers can see all drones for now as per "List all drones" requirement without restriction mentioned.
        # But let's keep the existing logic: Admins see all. Users see active ones.
        
        user = self.request.user
        if getattr(user, 'role', None) == 'admin' or user.is_staff:
             return queryset
        
        return queryset.filter(is_active=True)

    @action(detail=True, methods=['get'])
    def status(self, request, drone_id=None):
        """Get current status of a specific drone"""
        drone = self.get_object()
        
        try:
            status_obj = drone.status
            serializer = DroneStatusSerializer(status_obj)
            return Response(serializer.data)
        except DroneStatus.DoesNotExist:
            return Response(
                {'error': 'Status not available for this drone'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['patch'], permission_classes=[IsDroneAuthenticated])
    def update_status(self, request):
        """Update drone status (battery, signal) from ESP32"""
        # Drone retrieved from authentication
        drone = request.auth
        
        if not drone:
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
            
        status_obj, created = DroneStatus.objects.get_or_create(drone=drone)
        serializer = DroneStatusUpdateSerializer(status_obj, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def history(self, request, drone_id=None):
        """Get GPS location history for a drone"""
        drone = self.get_object()

        # Get query parameters
        limit = request.query_params.get('limit', 50)
        hours = request.query_params.get('hours', 24)

        try:
            limit = int(limit)
            hours = int(hours)
        except ValueError:
            return Response(
                {'error': 'Invalid limit or hours parameter'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Filter by time range
        since = timezone.now() - timedelta(hours=hours)
        locations = drone.gps_locations.filter(timestamp__gte=since).order_by('-timestamp')[:limit]

        serializer = GPSLocationSerializer(locations, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], permission_classes=[IsDroneAuthenticated])
    def location(self, request):
        """Update GPS location (from ESP32)"""
        # Drone retrieved from authentication
        drone = request.auth
        
        # Double check authentication (though permission class handles it)
        if not drone:
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )

        serializer = GPSLocationUpdateSerializer(data=request.data)
        
        if serializer.is_valid():
            lat = serializer.validated_data['latitude']
            lon = serializer.validated_data['longitude']
            alt = serializer.validated_data['altitude']
            
            location_point = Point(lon, lat)
            
            # Create new GPSLocation entry
            gps_location = GPSLocation.objects.create(
                drone=drone,
                location=location_point,
                altitude=alt
            )
            
            return Response(GPSLocationSerializer(gps_location).data, status=status.HTTP_201_CREATED)
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], permission_classes=[IsAdmin])
    def assign(self, request, drone_id=None):
        """Assign drone to officer"""
        drone = self.get_object()
        serializer = DroneAssignSerializer(data=request.data)
        
        if serializer.is_valid():
            officer_id = serializer.validated_data['officer_id']
            officer = get_object_or_404(User, pk=officer_id)
            
            # Check if user is an officer?
            # if officer.role != 'officer': ...
            
            drone.assigned_officer = officer
            drone.save()
            return Response({'status': 'assigned', 'officer': officer.email})
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], permission_classes=[IsAdmin])
    def activate(self, request, drone_id=None):
        """Activate drone"""
        drone = self.get_object()
        drone.is_active = True
        drone.save()
        return Response({'status': 'activated'})

    @action(detail=True, methods=['post'], permission_classes=[IsAdmin])
    def deactivate(self, request, drone_id=None):
        """Deactivate drone"""
        drone = self.get_object()
        drone.is_active = False
        drone.assigned_officer = None # Optional: unassign on deactivate?
        drone.save()
        return Response({'status': 'deactivated'})

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAdminUser])
    def inactive(self, request):
        """Get list of inactive drones (admin only)"""
        inactive_drones = self.get_queryset().filter(is_active=False)
        serializer = DroneSerializer(inactive_drones, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAdminUser])
    def unassigned(self, request):
        """Get list of unassigned drones (admin only)"""
        unassigned_drones = self.get_queryset().filter(assigned_officer__isnull=True)
        serializer = DroneSerializer(unassigned_drones, many=True)
        return Response(serializer.data)
