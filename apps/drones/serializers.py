from rest_framework import serializers
from django.contrib.gis.geos import Point
from ..models import Drone, DroneStatus, GPSLocation


class GPSLocationSerializer(serializers.ModelSerializer):
    """Serializer for GPS location data"""
    latitude = serializers.SerializerMethodField()
    longitude = serializers.SerializerMethodField()

    class Meta:
        model = GPSLocation
        fields = [
            'id', 'drone', 'location', 'latitude', 'longitude',
            'altitude', 'timestamp', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'timestamp', 'created_at', 'updated_at']

    def get_latitude(self, obj):
        return obj.latitude

    def get_longitude(self, obj):
        return obj.longitude

    def create(self, validated_data):
        # Handle location creation from lat/lng if provided
        if 'latitude' in self.initial_data and 'longitude' in self.initial_data:
            lat = self.initial_data['latitude']
            lng = self.initial_data['longitude']
            validated_data['location'] = Point(lng, lat)  # Point(longitude, latitude)
        return super().create(validated_data)


class DroneStatusSerializer(serializers.ModelSerializer):
    """Serializer for drone status information"""
    drone_name = serializers.CharField(source='drone.name', read_only=True)
    drone_id = serializers.CharField(source='drone.drone_id', read_only=True)

    class Meta:
        model = DroneStatus
        fields = [
            'id', 'drone', 'drone_name', 'drone_id', 'battery_level',
            'signal_strength', 'status', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class DroneSerializer(serializers.ModelSerializer):
    """Serializer for drone information"""
    status = DroneStatusSerializer(read_only=True)
    latest_location = GPSLocationSerializer(source='gps_locations', read_only=True)
    assigned_officer_name = serializers.CharField(
        source='assigned_officer.get_full_name',
        read_only=True
    )

    class Meta:
        model = Drone
        fields = [
            'id', 'drone_id', 'name', 'model', 'serial_number',
            'is_active', 'assigned_officer', 'assigned_officer_name',
            'status', 'latest_location', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def to_representation(self, instance):
        """Customize representation to include latest GPS location"""
        data = super().to_representation(instance)
        latest_gps = instance.gps_locations.first()
        if latest_gps:
            data['latest_location'] = GPSLocationSerializer(latest_gps).data
        return data


class DroneCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating drones (admin only)"""
    class Meta:
        model = Drone
        fields = [
            'drone_id', 'name', 'model', 'serial_number',
            'is_active', 'assigned_officer'
        ]


class DroneStatusUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating drone status"""
    class Meta:
        model = DroneStatus
        fields = ['battery_level', 'signal_strength', 'status']


class DroneAssignSerializer(serializers.Serializer):
    """Serializer for assigning a drone to an officer"""
    officer_id = serializers.IntegerField(required=True)


class GPSLocationUpdateSerializer(serializers.Serializer):
    """Serializer for updating GPS location"""
    latitude = serializers.FloatField(required=True)
    longitude = serializers.FloatField(required=True)
    altitude = serializers.FloatField(required=True)