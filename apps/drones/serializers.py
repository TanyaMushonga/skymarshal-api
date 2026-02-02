from rest_framework import serializers
from django.contrib.gis.geos import Point
import re
from .models import Drone, DroneStatus, GPSLocation


class GPSLocationSerializer(serializers.ModelSerializer):
    """Serializer for GPS location updates from drones"""
    latitude = serializers.FloatField(required=True)
    longitude = serializers.FloatField(required=True)

    class Meta:
        model = GPSLocation
        fields = [
            'id', 'drone', 'location', 'latitude', 'longitude',
            'altitude', 'timestamp', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'location', 'timestamp', 'created_at', 'updated_at']

    def validate_latitude(self, value):
        """Validate latitude is between -90 and 90"""
        if not -90 <= value <= 90:
            raise serializers.ValidationError("Latitude must be between -90 and 90")
        return value
    
    def validate_longitude(self, value):
        """Validate longitude is between -180 and 180"""
        if not -180 <= value <= 180:
            raise serializers.ValidationError("Longitude must be between -180 and 180")
        return value

    def validate_altitude(self, value):
        """Validate altitude is positive"""
        if value < 0:
            raise serializers.ValidationError("Altitude must be positive")
        return value

    def create(self, validated_data):
        # Handle location creation from lat/lng if provided
        latitude = validated_data.pop('latitude', None)
        longitude = validated_data.pop('longitude', None)
        
        if latitude is not None and longitude is not None:
             validated_data['location'] = Point(longitude, latitude)
             
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
    latest_location = serializers.SerializerMethodField()
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

    def get_latest_location(self, obj):
        latest = obj.gps_locations.order_by('-timestamp').first()
        if latest:
            return GPSLocationSerializer(latest).data
        return None


class DroneCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating drones (admin only)"""
    class Meta:
        model = Drone
        fields = [
            'drone_id', 'name', 'model', 'serial_number',
            'is_active', 'assigned_officer'
        ]


class DroneStatusUpdateSerializer(serializers.Serializer):
    """Serializer for drone status updates"""
    battery_level = serializers.IntegerField(min_value=0, max_value=100)
    signal_strength = serializers.IntegerField(min_value=0, max_value=100)

    def update(self, instance, validated_data):
        instance.battery_level = validated_data.get('battery_level', instance.battery_level)
        instance.signal_strength = validated_data.get('signal_strength', instance.signal_strength)
        instance.save()
        return instance


class DroneAssignSerializer(serializers.Serializer):
    """Serializer for assigning a drone to an officer"""
    officer_id = serializers.IntegerField(required=True)


class GPSLocationUpdateSerializer(serializers.Serializer):
    """Serializer for updating GPS location"""
    latitude = serializers.FloatField(required=True)
    longitude = serializers.FloatField(required=True)
    altitude = serializers.FloatField(required=True)


class StreamRegistrationSerializer(serializers.Serializer):
    """Serializer for stream registration from drones"""
    rtsp_url = serializers.URLField()
    resolution = serializers.CharField(default='1920x1080')
    frame_rate = serializers.IntegerField(default=30, min_value=1, max_value=60)
    
    def validate_rtsp_url(self, value):
        """Validate URL starts with rtsp://"""
        if not value.startswith('rtsp://'):
            raise serializers.ValidationError("URL must start with 'rtsp://'")
        return value
    
    def validate_resolution(self, value):
        """Validate resolution format (e.g., 1920x1080)"""
        if not re.match(r'^\d+x\d+$', value):
            raise serializers.ValidationError(
                "Resolution must be in format 'WIDTHxHEIGHT' (e.g., '1920x1080')"
            )
        return value