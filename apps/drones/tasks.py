from celery import shared_task
from django.utils import timezone
from datetime import timedelta
import logging
from .models import DroneAPIKey, DroneStatus
from apps.notifications.tasks import send_notification

logger = logging.getLogger(__name__)

@shared_task
def record_api_key_usage(api_key_id):
    try:
        api_key = DroneAPIKey.objects.get(id=api_key_id)
        api_key.record_usage()
    except DroneAPIKey.DoesNotExist:
        pass

@shared_task
def monitor_drone_health():
    """
    Periodic task to check drone health status.
    - Marks drones as 'offline' if no status update received in last 5 minutes.
    - Sends notifications for low battery (< 20%).
    """
    logger.info("Starting drone health check...")
    
    threshold = timezone.now() - timedelta(minutes=5)
    
    stale_statuses = DroneStatus.objects.filter(
        updated_at__lt=threshold,
        status__in=['online', 'maintenance']
    ).select_related('drone', 'drone__assigned_officer')
    
    for drone_status in stale_statuses:
        logger.warning(f"Drone {drone_status.drone.drone_id} is unresponsive. Marking as OFFLINE.")
        drone_status.status = 'offline'
        drone_status.save(update_fields=['status', 'updated_at'])
        
        # Notify assigned officer
        officer = drone_status.drone.assigned_officer
        if officer:
            send_notification.delay(
                user_id=officer.id,
                title="Drone Offline Alert",
                message=f"Drone {drone_status.drone.name} ({drone_status.drone.drone_id}) has gone offline due to inactivity.",
                notification_type='alert',
                related_object_id=str(drone_status.drone.id)
            )

 
    low_battery_drones = DroneStatus.objects.filter(
        battery_level__lt=20,
        status='online'
    ).select_related('drone', 'drone__assigned_officer')
    
    for drone_status in low_battery_drones:
        officer = drone_status.drone.assigned_officer
        if officer:
             send_notification.delay(
                user_id=officer.id,
                title="Low Battery Warning",
                message=f"Drone {drone_status.drone.name} battery is critical ({drone_status.battery_level}%). Return to base immediately.",
                notification_type='warning',
                related_object_id=str(drone_status.drone.id)
            )
            
    logger.info("Drone health check completed.")