from django.db import models
from django.contrib.gis.db import models as gis_models
from apps.core.models import TimestampedModel
from apps.drones.models import Drone

class Detection(TimestampedModel):
    drone = models.ForeignKey(Drone, on_delete=models.CASCADE, related_name='detections')
    patrol = models.ForeignKey('patrols.Patrol', on_delete=models.SET_NULL, null=True, blank=True, related_name='detections')
    timestamp = models.DateTimeField(db_index=True)
    frame_number = models.IntegerField()
    
    # Payload details
    vehicle_type = models.CharField(max_length=50) # car, truck, etc.
    confidence = models.FloatField()
    box_coordinates = models.JSONField() # [x1, y1, x2, y2]

    
    # Optional extended properties
    license_plate = models.CharField(max_length=20, null=True, blank=True)
    speed = models.FloatField(null=True, blank=True) # km/h
    track_id = models.IntegerField(null=True, blank=True)
    
    # Location where detection happened
    location = gis_models.PointField(geography=True, null=True, blank=True)
    altitude = models.FloatField(null=True, blank=True)
    image_snapshot = models.ImageField(upload_to='detections/', null=True, blank=True)

    class Meta:
        db_table = 'detections'
        ordering = ['-timestamp']
        constraints = [
            # Track-level uniqueness: one record per vehicle per patrol/drone
            models.UniqueConstraint(
                fields=['patrol', 'drone', 'track_id'], 
                name='unique_patrol_drone_track',
                condition=models.Q(patrol__isnull=False)
            ),
            # Fallback for untracked detections
            models.UniqueConstraint(
                fields=['drone', 'track_id'], 
                name='unique_drone_track_no_patrol',
                condition=models.Q(patrol__isnull=True)
            )
        ]
        indexes = [
            models.Index(fields=['drone', '-timestamp']),
        ]

    def __str__(self):
        return f"{self.vehicle_type} detected by {self.drone.drone_id} at {self.timestamp}"
