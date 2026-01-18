from celery import shared_task
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

@shared_task
def monitor_drone_health():
    """Periodic task to monitor drone health and status"""
    from .models import Drone
    
    try:
        drones = Drone.objects.filter(is_active=True)
        
        for drone in drones:
            # Get latest status
            latest_status = drone.status
            
            # Check if drone is offline (no status update in last 5 minutes)
            if latest_status:
                time_since_update = timezone.now() - latest_status.updated_at
                if time_since_update.total_seconds() > 300:  # 5 minutes
                    latest_status.status = 'offline'
                    latest_status.save()
                    logger.warning(f"Drone {drone.drone_id} marked as offline")
            
            # Check battery levels and send alerts
            if latest_status and latest_status.battery_level < 20:
                # Send low battery alert
                if drone.assigned_officer:
                    from apps.notifications.tasks import send_notification
                    send_notification.delay(
                        drone.assigned_officer.id,
                        {
                            'type': 'drone_alert',
                            'title': 'Low Battery Alert',
                            'message': f"Drone {drone.name} has low battery ({latest_status.battery_level}%)",
                            'data': {
                                'drone_id': drone.drone_id,
                                'battery_level': latest_status.battery_level
                            },
                            'send_email': True
                        }
                    )
            
            # Check signal strength
            if latest_status and latest_status.signal_strength < 30:
                # Send weak signal alert
                if drone.assigned_officer:
                    from apps.notifications.tasks import send_notification
                    send_notification.delay(
                        drone.assigned_officer.id,
                        {
                            'type': 'drone_alert',
                            'title': 'Weak Signal Alert',
                            'message': f"Drone {drone.name} has weak signal ({latest_status.signal_strength}%)",
                            'data': {
                                'drone_id': drone.drone_id,
                                'signal_strength': latest_status.signal_strength
                            }
                        }
                    )
        
        logger.info(f"Drone health monitoring completed for {drones.count()} drones")
        
    except Exception as e:
        logger.error(f"Error monitoring drone health: {e}")