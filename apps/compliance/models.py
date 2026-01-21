from django.db import models
from apps.core.models import TimestampedModel
from apps.vehicle_lookup.models import VehicleRegistration

class ComplianceScore(TimestampedModel):
    vehicle = models.OneToOneField(VehicleRegistration, on_delete=models.CASCADE, related_name='compliance_score')
    safe_driving_points = models.IntegerField(default=0)
    last_observation = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.vehicle.license_plate}: {self.safe_driving_points} pts"

class LotteryEvent(TimestampedModel):
    STATUS_CHOICES = (
        ('OPEN', 'Open'),
        ('DRAWN', 'Drawn'),
        ('PAID', 'Paid'),
    )
    
    name = models.CharField(max_length=100)
    draw_date = models.DateField()
    pool_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OPEN')
    
    warnings = models.TextField(blank=True, help_text="Any issues during draw")
    
    # Winners link
    winners = models.ManyToManyField(VehicleRegistration, related_name='lottery_wins', blank=True)
    
    def __str__(self):
        return f"{self.name} - {self.status} (${self.pool_amount})"
