from rest_framework import serializers
from .models import VehicleRegistration

class VehicleRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleRegistration
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']
