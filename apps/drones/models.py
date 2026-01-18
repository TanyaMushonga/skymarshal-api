from django.db import models
from apps.core.models import TimestampedModel


class Drone(TimestampedModel):
    drone_id = models.CharField(max_length=50, unique=True, db_index=True)
    name = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    serial_number = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)
    assigned_officer = models.ForeignKey(
        'users.User', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='assigned_drones'
    )
    
    class Meta:
        db_table = 'drones'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.drone_id})"


class DroneStatus(TimestampedModel):
    drone = models.OneToOneField(Drone, on_delete=models.CASCADE, related_name='status')
    battery_level = models.IntegerField(default=100)
    signal_strength = models.IntegerField(default=100)
    status = models.CharField(
        max_length=20, 
        choices=[
            ('online', 'Online'),
            ('offline', 'Offline'),
            ('maintenance', 'Maintenance'),
            ('error', 'Error')
        ],
        default='offline'
    )
    
    class Meta:
        db_table = 'drone_status'
    
    def __str__(self):
        return f"Status for {self.drone.name}"


class GPSLocation(TimestampedModel):
    drone = models.ForeignKey(Drone, on_delete=models.CASCADE, related_name='gps_locations')
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    altitude = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = 'gps_locations'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['drone', '-timestamp']),
        ]
    
    def __str__(self):
        return f"GPS for {self.drone.name} at {self.timestamp}"
