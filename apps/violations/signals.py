from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.detections.models import Detection
from .models import Violation
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Detection)
def check_for_violations(sender, instance, created, **kwargs):
    """
    Signal to check each new Detection for potential violations.
    Only checks for speeding based on the drone's configured speed limit.
    """
    if not created:
        return

    try:
        # Resolve Speed Limit
        # Priority: Patrol Config -> Drone Default -> Global Default (60.0)
        limit = 60.0
        
        if instance.patrol and instance.patrol.patrol_config:
            # Check for 'speed_limit' in config (could be string or int)
            cfg_limit = instance.patrol.patrol_config.get('speed_limit')
            if cfg_limit:
                limit = float(cfg_limit)
        elif hasattr(instance.drone, 'speed_limit'):
            limit = instance.drone.speed_limit
        
        # Check Violation
        if instance.speed and instance.speed > limit:
            
            # Construct Immutable Evidence Pack
            evidence_data = {
                'violation_speed': instance.speed,
                'zone_limit': limit,
                'coordinates': {
                    'lat': instance.location.y if instance.location else None,
                    'lon': instance.location.x if instance.location else None,
                },
                'altitude': instance.altitude,
                'drone_id': instance.drone.drone_id,
                'patrol_id': instance.patrol.id if instance.patrol else None,
                'timestamp': instance.timestamp.isoformat()
            }

            Violation.objects.create(
                detection=instance,
                patrol=instance.patrol,
                violation_type='SPEEDING',
                fine_amount=50.00, # Base fine logic could be dynamic too
                evidence_meta=evidence_data,
                description=f"Vehicle detected at {instance.speed} km/h (Limit: {limit} km/h)"
            )
            logger.info(f"Speeding violation created for Detection {instance.id} (Patrol Limit: {limit})")

    except Exception as e:
        logger.error(f"Error checking violations for Detection {instance.id}: {e}", exc_info=True)
