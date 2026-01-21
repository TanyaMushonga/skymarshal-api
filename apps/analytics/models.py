from django.contrib.gis.db import models
from django.db.models import Index
from apps.core.models import TimestampedModel
from django.contrib.auth import get_user_model

User = get_user_model()

class Recommendation(TimestampedModel):
    CATEGORY_CHOICES = (
        ('ALLOCATION', 'Resource Allocation'),
        ('SAFETY', 'Safety Improvement'),
        ('MAINTENANCE', 'Maintenance Needed'),
        ('POLICY', 'Policy Adjustment'),
    )
    
    title = models.CharField(max_length=255)
    description = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='ALLOCATION')
    confidence_score = models.FloatField(help_text="Confidence level 0.0 to 1.0")
    metadata = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"[{self.category}] {self.title} ({self.confidence_score*100:.0f}%)"

class TrafficMetrics(models.Model):
    """
    Time-series traffic metrics aggregated every 5 minutes
    """
    timestamp = models.DateTimeField(db_index=True)  # Not PK, as multiple drones have same timestamp
    location = models.PointField()
    drone_id = models.CharField(max_length=100)
    
    # Volume metrics
    vehicle_count = models.IntegerField(default=0)
    car_count = models.IntegerField(default=0)
    truck_count = models.IntegerField(default=0)
    motorcycle_count = models.IntegerField(default=0)
    bus_count = models.IntegerField(default=0)
    
    # Speed metrics
    average_speed = models.FloatField(default=0.0)
    max_speed = models.FloatField(default=0.0)
    min_speed = models.FloatField(default=0.0)
    speed_variance = models.FloatField(default=0.0)
    
    # Violation metrics
    violation_count = models.IntegerField(default=0)
    citation_count = models.IntegerField(default=0)
    
    # Metadata
    sample_size = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'traffic_metrics'
        managed = True # Standard table for now
        indexes = [
            Index(fields=['timestamp', 'location']),
            Index(fields=['drone_id', 'timestamp'])
        ]

class HeatMap(TimestampedModel):
    """
    Grid-based heat map data for visualizing traffic patterns
    """
    date = models.DateField(db_index=True)
    hour = models.IntegerField() # 0-23
    metric_type = models.CharField(max_length=50) # 'speed', 'volume', 'violations'
    
    # Grid data - JSON structure
    location_grid = models.JSONField()
    
    # Bounds
    min_lat = models.FloatField()
    max_lat = models.FloatField()
    min_lon = models.FloatField()
    max_lon = models.FloatField()
    
    class Meta:
        db_table = 'heat_maps'
        unique_together = ['date', 'hour', 'metric_type']
        indexes = [
            Index(fields=['date', 'hour']),
            Index(fields=['metric_type', 'date'])
        ]

class TrafficPattern(TimestampedModel):
    """
    Identified traffic patterns for predictive analysis
    """
    PATTERN_TYPES = (
        ('peak_hour', 'Peak Hour'),
        ('congestion', 'Congestion Zone'),
        ('accident_prone', 'Accident Prone Area'),
    )
    
    pattern_type = models.CharField(max_length=50, choices=PATTERN_TYPES)
    location = models.PointField()
    location_name = models.CharField(max_length=255, blank=True)
    
    # Time pattern
    days_of_week = models.JSONField() # [0, 1, 2...]
    start_hour = models.IntegerField()
    end_hour = models.IntegerField(null=True, blank=True)
    
    # Pattern characteristics
    avg_vehicle_count = models.FloatField(default=0.0)
    avg_speed = models.FloatField(default=0.0)
    violation_rate = models.FloatField(default=0.0)
    
    confidence_score = models.FloatField(default=0.0)
    sample_size = models.IntegerField(default=0)
    
    recommendations = models.TextField(blank=True)
    
    class Meta:
        db_table = 'traffic_patterns'
        indexes = [
            Index(fields=['pattern_type', 'confidence_score']),
        ]

class AnalyticsReport(TimestampedModel):
    """
    Generated analytics reports
    """
    REPORT_TYPES = (
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('custom', 'Custom'),
    )
    
    report_type = models.CharField(max_length=50, choices=REPORT_TYPES)
    title = models.CharField(max_length=255)
    start_date = models.DateField()
    end_date = models.DateField()
    
    report_data = models.JSONField()
    summary = models.TextField(blank=True)
    
    # File attachments (using FileField, requires media config)
    pdf_file = models.FileField(upload_to='reports/', null=True, blank=True)
    excel_file = models.FileField(upload_to='reports/', null=True, blank=True)
    
    generated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    is_public = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'analytics_reports'
        ordering = ['-created_at']
