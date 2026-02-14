from rest_framework import serializers
from .models import Patrol
from apps.detections.serializers import DetectionSerializer
from apps.violations.serializers import ViolationSerializer

class PatrolSerializer(serializers.ModelSerializer):
    detections = DetectionSerializer(many=True, read_only=True)
    violations = ViolationSerializer(many=True, read_only=True)
    
    # helper identifiers
    drone_id_str = serializers.CharField(source='drone.drone_id', read_only=True)
    officer_email = serializers.CharField(source='officer.email', read_only=True)
    
    # Live stats
    battery_level = serializers.IntegerField(source='drone.status.battery_level', read_only=True)
    status_display = serializers.CharField(source='drone.status.status', read_only=True)
    latest_location = serializers.SerializerMethodField()
    flight_duration_seconds = serializers.SerializerMethodField()
    detection_count = serializers.SerializerMethodField()
    violation_count = serializers.SerializerMethodField()

    class Meta:
        model = Patrol
        fields = [
            'id', 'drone', 'drone_id_str', 'officer', 'officer_email', 
            'start_time', 'end_time', 'patrol_config', 'status', 'created_at',
            'battery_level', 'status_display', 'latest_location', 
            'flight_duration_seconds', 'detection_count', 'violation_count',
            'detections', 'violations'
        ]
        read_only_fields = ['start_time', 'end_time', 'status', 'created_at']

    def get_latest_location(self, obj):
        from apps.drones.serializers import GPSLocationSerializer
        latest = obj.drone.gps_locations.order_by('-timestamp').first()
        if latest:
            return GPSLocationSerializer(latest).data
        return None

    def get_flight_duration_seconds(self, obj):
        from django.utils import timezone
        if obj.status == 'ACTIVE':
            delta = timezone.now() - obj.start_time
            return int(delta.total_seconds())
        if obj.end_time:
            delta = obj.end_time - obj.start_time
            return int(delta.total_seconds())
        return 0

    def get_detection_count(self, obj):
        return obj.detections.count()

    def get_violation_count(self, obj):
        return obj.violations.count()
