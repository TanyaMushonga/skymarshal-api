from django.db import models
from django.contrib.gis.db import models as gis_models
from django.utils import timezone
import secrets
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
    location = gis_models.PointField(geography=True) 
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
    
    @property
    def latitude(self):
        """Convenience property to access latitude (y-coordinate)"""
        return self.location.y if self.location else None
    
    @property
    def longitude(self):
        """Convenience property to access longitude (x-coordinate)"""
        return self.location.x if self.location else None    


class DroneAPIKey(TimestampedModel):
    """
    API key authentication for ESP32-CAM drones
    Each drone gets a unique API key for authentication
    """
    drone = models.OneToOneField(Drone, on_delete=models.CASCADE, related_name='api_key')
    key = models.CharField(max_length=128, unique=True, db_index=True, editable=False)
    is_active = models.BooleanField(default=True)
    last_used = models.DateTimeField(null=True, blank=True)
    usage_count = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'drone_api_keys'
        
    def __str__(self):
        return f"API Key for {self.drone.drone_id}"
        
    @classmethod
    def generate_key(cls):
        """
        Generate a secure API key in format: sk_drone_{random_32_chars}
        """
        return f"sk_drone_{secrets.token_urlsafe(32)}"
        
    def save(self, *args, **kwargs):
        """
        Override save to auto-generate key if not exists
        """
        if not self.key:
            self.key = self.generate_key()
        super().save(*args, **kwargs)
        
    def record_usage(self):
        """
        Update last_used to now() and increment usage_count by 1
        """
        self.last_used = timezone.now()
        self.usage_count += 1
        self.save(update_fields=['last_used', 'usage_count'])
