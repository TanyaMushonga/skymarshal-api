from django.db import models
from django.conf import settings
from apps.core.models import TimestampedModel
import uuid

class Notification(TimestampedModel):
    """
    Model to store user notifications
    """
    TYPE_CHOICES = (
        ('violation_detected', 'Violation Detected'),
        ('patrol_started', 'Patrol Started'),
        ('patrol_ended', 'Patrol Ended'),
        ('low_battery', 'Low Battery'),
        ('stream_health', 'Stream Health'),
        ('mission_update', 'Mission Update'),
        ('system_alert', 'System Alert'),
        ('emergency', 'Emergency'),
        ('general', 'General'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='notifications'
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(max_length=50, choices=TYPE_CHOICES, default='general')
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # Optional: Link to related object
    related_object_id = models.CharField(max_length=255, null=True, blank=True)
    
    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['recipient', '-created_at']),
        ]

    def __str__(self):
        return f"{self.title} - {self.recipient}"
