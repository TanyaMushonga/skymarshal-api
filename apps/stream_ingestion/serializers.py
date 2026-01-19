from rest_framework import serializers
from django.utils import timezone
from .models import VideoStream, StreamSession
from apps.drones.models import Drone


class VideoStreamSerializer(serializers.ModelSerializer):
    """Serializer for VideoStream model with nested drone info and computed fields"""
    drone_id = serializers.CharField(source='drone.drone_id', read_only=True)
    drone_name = serializers.CharField(source='drone.name', read_only=True)
    is_streaming = serializers.SerializerMethodField()
    active_session_id = serializers.SerializerMethodField()

    class Meta:
        model = VideoStream
        fields = [
            'id', 'stream_id', 'drone', 'drone_id', 'drone_name', 'rtsp_url',
            'is_active', 'frame_rate', 'resolution', 'is_streaming',
            'active_session_id', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'stream_id', 'created_at', 'updated_at']

    def get_is_streaming(self, obj):
        """Check if stream has an active session"""
        return obj.sessions.filter(end_time__isnull=True).exists()

    def get_active_session_id(self, obj):
        """Get the ID of the current active session"""
        active_session = obj.sessions.filter(end_time__isnull=True).first()
        return active_session.id if active_session else None


class StreamSessionSerializer(serializers.ModelSerializer):
    """Serializer for StreamSession model with computed fields"""
    stream_id = serializers.UUIDField(source='stream.stream_id', read_only=True)
    stream_drone_name = serializers.CharField(source='stream.drone.name', read_only=True)
    duration = serializers.SerializerMethodField()
    frames_per_second = serializers.SerializerMethodField()

    class Meta:
        model = StreamSession
        fields = [
            'id', 'stream', 'stream_id', 'stream_drone_name', 'start_time',
            'end_time', 'frames_processed', 'kafka_topic', 'duration',
            'frames_per_second', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_duration(self, obj):
        """Calculate session duration in seconds"""
        end_time = obj.end_time or timezone.now()
        delta = end_time - obj.start_time
        return delta.total_seconds()

    def get_frames_per_second(self, obj):
        """Calculate frames per second"""
        duration = self.get_duration(obj)
        if duration > 0:
            return obj.frames_processed / duration
        return 0


class StreamRegistrationSerializer(serializers.Serializer):
    """Serializer for registering new video streams"""
    drone_id = serializers.CharField(max_length=50, required=True)
    rtsp_url = serializers.URLField(max_length=500, required=True)
    resolution = serializers.CharField(max_length=20, default='1920x1080')
    frame_rate = serializers.IntegerField(min_value=1, max_value=60, default=30)

    def validate_drone_id(self, value):
        """Validate that drone exists"""
        try:
            drone = Drone.objects.get(drone_id=value)
            return value
        except drone.DoesNotExist:
            raise serializers.ValidationError("Drone with this ID does not exist.")

    def validate_rtsp_url(self, value):
        """Validate RTSP URL format"""
        if not value.startswith('rtsp://'):
            raise serializers.ValidationError("URL must be a valid RTSP URL starting with rtsp://")
        return value

    def validate_resolution(self, value):
        """Validate resolution format (e.g., 1920x1080)"""
        if 'x' not in value:
            raise serializers.ValidationError("Resolution must be in format WIDTHxHEIGHT (e.g., 1920x1080)")
        try:
            width, height = value.split('x')
            int(width), int(height)
        except ValueError:
            raise serializers.ValidationError("Resolution must contain valid integer dimensions")
        return value

    def create(self, validated_data):
        """Create VideoStream from validated data"""
        drone_id = validated_data.pop('drone_id')
        drone = Drone.objects.get(drone_id=drone_id)
        return VideoStream.objects.create(drone=drone, **validated_data)