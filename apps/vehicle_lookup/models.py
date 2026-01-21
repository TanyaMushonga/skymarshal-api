from django.db import models
from apps.core.models import TimestampedModel

class VehicleRegistration(TimestampedModel):
    STATUS_CHOICES = (
        ('ACTIVE', 'Active'),
        ('EXPIRED', 'Expired'),
        ('STOLEN', 'Stolen'),
        ('SUSPENDED', 'Suspended'),
    )

    license_plate = models.CharField(max_length=20, unique=True, db_index=True)
    owner_name = models.CharField(max_length=255)
    owner_phone_number = models.CharField(max_length=20, null=True, blank=True)
    make = models.CharField(max_length=50)
    model = models.CharField(max_length=50)
    color = models.CharField(max_length=30)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    expiry_date = models.DateField(null=True, blank=True)

    class Meta:
        db_table = 'vehicle_registrations'
        verbose_name = 'Vehicle Registration'
        verbose_name_plural = 'Vehicle Registrations'

    def __str__(self):
        return f"{self.license_plate} - {self.make} {self.model} ({self.status})"
