from django.db import models
from apps.core.models import TimestampedModel
import uuid


class VideoStream(TimestampedModel):
    stream_id = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    drone = models.ForeignKey('drones.Drone', on_delete=models.CASCADE, related_name='streams')
    rtsp_url = models.URLField(max_length=500)
    is_active = models.BooleanField(default=False)
    frame_rate = models.IntegerField(default=30)
    resolution = models.CharField(max_length=20, default='1920x1080')
    
    class Meta:
        db_table = 'video_streams'
    
    def __str__(self):
        return f"Stream {self.stream_id} - {self.drone.name}"


class StreamSession(TimestampedModel):
    stream = models.ForeignKey(VideoStream, on_delete=models.CASCADE, related_name='sessions')
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    frames_processed = models.IntegerField(default=0)
    kafka_topic = models.CharField(max_length=100)
    
    class Meta:
        db_table = 'stream_sessions'
        indexes = [
            models.Index(fields=['stream', '-start_time']),
        ]
    
    def __str__(self):
        return f"Session {self.id} for {self.stream.stream_id}"