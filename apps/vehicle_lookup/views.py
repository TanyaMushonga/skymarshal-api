from rest_framework import viewsets, permissions, filters
from .models import VehicleRegistration
from .serializers import VehicleRegistrationSerializer

class VehicleRegistrationViewSet(viewsets.ModelViewSet):
    queryset = VehicleRegistration.objects.all()
    serializer_class = VehicleRegistrationSerializer
    permission_classes = [permissions.IsAdminUser]  # Only admins can manage vehicles
    
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['license_plate', 'owner_name', 'make', 'model']
    ordering_fields = ['license_plate', 'status', 'created_at']
    ordering = ['-created_at']
