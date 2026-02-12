from celery import shared_task
from django.utils import timezone
from datetime import timedelta, datetime, time
from django.db.models import Avg, Sum, Count, Min, Max, F
from django.db.models.functions import ExtractHour
from django.contrib.gis.geos import Point
from .models import TrafficMetrics, HeatMap, TrafficPattern, AnalyticsReport
from apps.detections.models import Detection
from apps.violations.models import Violation
from apps.drones.models import Drone
import logging
import numpy as np

logger = logging.getLogger(__name__)

@shared_task
def aggregate_traffic_metrics():
    """ 
    Aggregates detection data into TrafficMetrics every 5 minutes.
    """
    now = timezone.now().replace(second=0, microsecond=0)
    five_min_ago = now - timedelta(minutes=5)
    
    active_drones = Drone.objects.all() # Or filter by status if available
    
    for drone in active_drones:
        detections = Detection.objects.filter(
            drone=drone,
            timestamp__gte=five_min_ago,
            timestamp__lt=now
        )
        
        if not detections.exists():
            continue
            
        # Simplified aggregation: Detection model is per-frame or per-event. 
        # Assuming one detection per vehicle for simplicity here, or use track_id distinct
        unique_vehicles = detections.values('track_id').distinct().count()
        vehicle_types = detections.values('vehicle_type').annotate(count=Count('track_id', distinct=True))
        
        type_counts = {item['vehicle_type']: item['count'] for item in vehicle_types}
        
        # Calculate speeds
        avg_speed = detections.aggregate(avg=Avg('speed'))['avg'] or 0.0
        max_speed = detections.aggregate(max=Max('speed'))['max'] or 0.0
        min_speed = detections.aggregate(min=Min('speed'))['min'] or 0.0
        
        # Calculate variance manually or approx
        speeds = list(detections.values_list('speed', flat=True))
        variance = np.var(speeds) if speeds else 0.0
        
        # Violations
        violations = Violation.objects.filter(
            detection__drone=drone,
            created_at__gte=five_min_ago,
            created_at__lt=now
        )
        
        # Get latest GPS location
        gps = drone.gps_locations.order_by('-timestamp').first()
        location = Point(gps.longitude, gps.latitude) if gps else Point(0,0)
        
        TrafficMetrics.objects.create(
            timestamp=now,
            location=location,
            drone_id=drone.drone_id,
            vehicle_count=unique_vehicles,
            car_count=type_counts.get('car', 0),
            truck_count=type_counts.get('truck', 0),
            motorcycle_count=type_counts.get('motorcycle', 0),
            bus_count=type_counts.get('bus', 0),
            average_speed=avg_speed,
            max_speed=max_speed,
            min_speed=min_speed,
            speed_variance=variance,
            violation_count=violations.count(),
            citation_count=violations.filter(status='CITATION_SENT').count(), # Corrected from conceptual check
            sample_size=len(speeds)
        )
        logger.info(f"Aggregated metrics for {drone.drone_id}")

@shared_task
def generate_heat_map(date_str=None, hour=None):
    """
    Generates hourly heat map data.
    """
    if not date_str:
        target_date = timezone.now().date()
    else:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        
    if hour is None:
        hour = timezone.now().hour
        
    # Define time range
    start_time = timezone.make_aware(datetime.combine(target_date, time(hour, 0)))
    end_time = start_time + timedelta(hours=1)
    
    # 1. Fetch Detections
    detections = Detection.objects.filter(
        timestamp__gte=start_time,
        timestamp__lt=end_time
    )
    
    if not detections.exists():
        return

    # 2. Grid Logic ( Simplified 100m grid logic )
    # Getting strict bounds
    lats = list(detections.values_list('location__y', flat=True)) # Point(x, y) -> (lon, lat)
    lons = list(detections.values_list('location__x', flat=True))
    
    if not lats: return

    min_lat, max_lat = min(lats), max(lats)
    min_lon, max_lon = min(lons), max(lons)

    # Simplified Heatmap: Just list points with weights for checking
    cells = []
    # Real implementation would bin these properly. 
    # For now, let's just aggregate by rounded coordinates to simulate grid
    grid_res = 0.001 # approx 100m
    
    grid = {} # (lat_idx, lon_idx) -> count
    
    for d in detections:
        lat_idx = int(d.location.y / grid_res)
        lon_idx = int(d.location.x / grid_res)
        key = (lat_idx, lon_idx)
        grid[key] = grid.get(key, 0) + 1
        
    for (lat_idx, lon_idx), count in grid.items():
        # Determine color
        if count < 10: color = '#00FF00'
        elif count < 50: color = '#FFFF00'
        else: color = '#FF0000'
        
        cells.append({
            'lat': lat_idx * grid_res,
            'lon': lon_idx * grid_res,
            'value': count,
            'color': color
        })
        
    HeatMap.objects.update_or_create(
        date=target_date,
        hour=hour,
        metric_type='volume',
        defaults={
            'location_grid': {'cells': cells},
            'min_lat': min_lat,
            'max_lat': max_lat,
            'min_lon': min_lon,
            'max_lon': max_lon
        }
    )

@shared_task
def detect_traffic_patterns():
    """
    Daily task to find recurring patterns
    """
    # Look at last 30 days metrics
    cutoff = timezone.now() - timedelta(days=30)
    metrics = TrafficMetrics.objects.filter(timestamp__gte=cutoff)
    
    # Simple Heuristic: High Average Volume @ Hour X
    # Group by hour
    hour_stats = metrics.annotate(hour=ExtractHour('timestamp')).values('hour').annotate(avg_vol=Avg('vehicle_count'))
    
    for stat in hour_stats:
        if stat['avg_vol'] > 100: # Threshold
            # Find center location
            center = Point(0,0) # Placeholder
            TrafficPattern.objects.update_or_create(
                pattern_type='peak_hour',
                start_hour=stat['hour'],
                defaults={
                    'location': center,
                    'days_of_week': [0,1,2,3,4], # Assume weekdays
                    'avg_vehicle_count': stat['avg_vol'],
                    'confidence_score': 0.85,
                    'recommendations': f"Peak traffic detected at {stat['hour']}:00. Deploy traffic control."
                }
            )

@shared_task
def generate_weekly_report():
    """
    Generates a generic weekly report summary.
    """
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=7)
    
    total_violations = Violation.objects.filter(created_at__date__gte=start_date).count()
    
    report_data = {
        'period': f"{start_date} to {end_date}",
        'total_violations': total_violations,
        'system_health': 'Good'
    }
    
    AnalyticsReport.objects.create(
        report_type='weekly',
        title=f"Weekly Report {start_date}",
        start_date=start_date,
        end_date=end_date,
        report_data=report_data,
        summary=f"Total violations this week: {total_violations}"
    )
