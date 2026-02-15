from rest_framework import serializers
from .models import Violation
from apps.vehicle_lookup.models import VehicleRegistration
from apps.vehicle_lookup.serializers import VehicleRegistrationSerializer
from apps.detections.serializers import DetectionSerializer

class ViolationSerializer(serializers.ModelSerializer):
    detection = DetectionSerializer(read_only=True)
    vehicle_details = serializers.SerializerMethodField()

    class Meta:
        model = Violation
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']

    def get_vehicle_details(self, obj):
        """
        Lookup vehicle and owner details based on the detected license plate.
        """
        license_plate = obj.detection.license_plate
        if not license_plate:
            return None
            
        try:
            vehicle = VehicleRegistration.objects.get(license_plate=license_plate)
            return VehicleRegistrationSerializer(vehicle).data
        except VehicleRegistration.DoesNotExist:
            return None
