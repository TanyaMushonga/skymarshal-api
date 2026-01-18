from rest_framework import serializers
from .models import Drone, Telemetry

class TelemetrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Telemetry
        fields = '__all__'
        read_only_fields = ('timestamp',)

class DroneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Drone
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')
