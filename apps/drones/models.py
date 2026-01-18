from django.db import models

class Drone(models.Model):
    STATUS_CHOICES = (
        ('IDLE', 'Idle'),
        ('PATROLLING', 'Patrolling'),
        ('RETURNING', 'Returning'),
        ('CHARGING', 'Charging'),
        ('MAINTENANCE', 'Maintenance'),
    )

    serial_number = models.CharField(max_length=100, unique=True)
    model_type = models.CharField(max_length=100)
    max_speed = models.FloatField(default=0.0, help_text="Max speed in km/h")
    battery_capacity = models.FloatField(default=100.0, help_text="Battery capacity in Wh")
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='IDLE')
    current_battery_level = models.FloatField(default=100.0, help_text="Current battery percentage")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.model_type} ({self.serial_number})"

class Telemetry(models.Model):
    drone = models.ForeignKey(Drone, on_delete=models.CASCADE, related_name='telemetry_logs')
    latitude = models.FloatField()
    longitude = models.FloatField()
    altitude = models.FloatField(help_text="Altitude in meters")
    speed = models.FloatField(help_text="Current speed in km/h")
    battery_percentage = models.FloatField()
    heading = models.FloatField(help_text="Heading in degrees")
    signal_strength = models.FloatField(null=True, blank=True, help_text="Signal strength in dBm or percentage")
    
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name_plural = "Telemetry Logs"

    def __str__(self):
        return f"Telemetry for {self.drone.serial_number} at {self.timestamp}"
