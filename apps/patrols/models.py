from django.db import models
from apps.core.models import TimestampedModel

class Patrol(TimestampedModel):
    STATUS_CHOICES = (
        ('ACTIVE', 'Active'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    )

    drone = models.ForeignKey(
        'drones.Drone', 
        on_delete=models.CASCADE, 
        related_name='patrols'
    )
    officer = models.ForeignKey(
        'users.User', 
        on_delete=models.CASCADE, 
        related_name='patrols'
    )
    
    start_time = models.DateTimeField(auto_now_add=True, db_index=True)
    end_time = models.DateTimeField(null=True, blank=True)
    
    # Configuration snapshot for this patrol
    # Stores: speed_limit, restricted_zones, flight_path_points, etc.
    patrol_config = models.JSONField(default=dict, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')

    class Meta:
        db_table = 'patrols'
        ordering = ['-start_time']

    def __str__(self):
        return f"Patrol {self.id} - {self.officer.email} - {self.drone.drone_id}"
