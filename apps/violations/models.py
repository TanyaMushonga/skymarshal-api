from django.db import models
from apps.core.models import TimestampedModel
from apps.detections.models import Detection

class Violation(TimestampedModel):
    STATUS_CHOICES = (
        ('NEW', 'New'),
        ('PROCESSED', 'Processed'),
        ('CITATION_SENT', 'Citation Sent'),
        ('DISMISSED', 'Dismissed'),
    )

    detection = models.OneToOneField(Detection, on_delete=models.CASCADE, related_name='violation')
    patrol = models.ForeignKey('patrols.Patrol', on_delete=models.SET_NULL, null=True, blank=True, related_name='violations')
    violation_type = models.CharField(max_length=50, default='SPEEDING')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='NEW')
    fine_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    # Metadata snapshot at time of violation
    description = models.TextField(blank=True)
    
    # Evidence Pack
    video_clip = models.FileField(upload_to='evidence/videos/', null=True, blank=True)
    image_snapshot = models.ImageField(upload_to='evidence/images/', null=True, blank=True)
    
    evidence_meta = models.JSONField(default=dict, blank=True)
    
    def __str__(self):
        return f"{self.violation_type} - {self.detection.drone.drone_id} ({self.status})"
