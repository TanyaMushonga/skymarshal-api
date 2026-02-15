from django.db import models
from apps.core.models import TimestampedModel

class VehicleRegistration(TimestampedModel):
    license_plate = models.CharField(max_length=20, unique=True, db_index=True)
    owner_name = models.CharField(max_length=255)
    owner_phone_number = models.CharField(max_length=20, null=True, blank=True)
    make = models.CharField(max_length=50)
    model = models.CharField(max_length=50)
    color = models.CharField(max_length=30)
    expiry_date = models.DateField(null=True, blank=True)
    license_points = models.IntegerField(default=100)
    license_status = models.CharField(
        max_length=20, 
        choices=(('ACTIVE', 'Active'), ('REVOKED', 'Revoked')), 
        default='ACTIVE'
    )

    class Meta:
        db_table = 'vehicle_registrations'
        verbose_name = 'Vehicle Registration'
        verbose_name_plural = 'Vehicle Registrations'

    def __str__(self):
        return f"{self.license_plate} - {self.make} {self.model}"
