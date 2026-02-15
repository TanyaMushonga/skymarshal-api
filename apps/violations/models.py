from django.db import models
from apps.core.models import TimestampedModel
from apps.detections.models import Detection

class Violation(TimestampedModel):
    STATUS_CHOICES = (
        ('NEW', 'New'),
        ('PROCESSED', 'Processed'),
        ('CITATION_SENT', 'Citation Sent'),
        ('DISMISSED', 'Dismissed'),
        ('PAID', 'Paid'),
        ('PARTIAL', 'Partial Payment'),
    )

    detection = models.OneToOneField(Detection, on_delete=models.CASCADE, related_name='violation')
    vehicle = models.ForeignKey('vehicle_lookup.VehicleRegistration', on_delete=models.SET_NULL, null=True, blank=True, related_name='violations')
    patrol = models.ForeignKey('patrols.Patrol', on_delete=models.SET_NULL, null=True, blank=True, related_name='violations')
    violation_type = models.CharField(max_length=50, default='SPEEDING')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='NEW')
    fine_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    # Metadata snapshot at time of violation
    description = models.TextField(blank=True)
    
    # Evidence Pack
    video_clip = models.FileField(upload_to='evidence/videos/', null=True, blank=True)
    image_snapshot = models.ImageField(upload_to='evidence/images/', null=True, blank=True)
    
    evidence_meta = models.JSONField(default=dict, blank=True)
    
    def __str__(self):
        return f"{self.violation_type} - {self.detection.drone.drone_id} ({self.status})"

class ViolationPayment(TimestampedModel):
    CURRENCY_CHOICES = (
        ('USD', 'US Dollar'),
        ('ZIG', 'Zimbabwe Gold (ZiG)'),
    )
    METHOD_CHOICES = (
        ('CASH', 'Cash'),
        ('WIRE_TRANSFER', 'Wire Transfer'),
    )

    violation = models.ForeignKey(Violation, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, choices=CURRENCY_CHOICES, default='USD')
    method = models.CharField(max_length=20, choices=METHOD_CHOICES, default='CASH')
    officer = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        db_table = 'violation_payments'
        verbose_name = 'Violation Payment'
        verbose_name_plural = 'Violation Payments'

    def __str__(self):
        return f"Payment of {self.amount} {self.currency} for {self.violation.id}"
