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
        fine = 50.00
        
        if instance.patrol and instance.patrol.patrol_config:
            # Check for 'speed_limit' in config (could be string or int)
            cfg_limit = instance.patrol.patrol_config.get('speed_limit')
            if cfg_limit:
                limit = float(cfg_limit)
            
            # Resolve Dynamic Fine
            cfg_fine = instance.patrol.patrol_config.get('fine_amount')
            if cfg_fine:
                fine = float(cfg_fine)

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

            violation = Violation.objects.create(
                detection=instance,
                patrol=instance.patrol,
                violation_type='SPEEDING',
                fine_amount=fine, 
                evidence_meta=evidence_data,
                description=f"Vehicle detected at {instance.speed} km/h (Limit: {limit} km/h)"
            )
            logger.info(f"Speeding violation created for Detection {instance.id} (Patrol Limit: {limit}, Fine: {fine})")

            # --- Notifications ---
            from apps.notifications.tasks import send_notification, send_sms_to_citizen
            from apps.vehicle_lookup.models import VehicleRegistration

            # 1. Notify Officer (WebSocket)
            if instance.patrol and instance.patrol.officer:
                send_notification.delay(
                    user_id=instance.patrol.officer.id,
                    title="Speeding Violation Detected",
                    message=f"Violation recorded by {instance.drone.drone_id}. Speed: {instance.speed} km/h",
                    notification_type="violation_alert",
                    related_object_id=str(violation.id)
                )

            # 2. Notify Citizen (SMS)
            if instance.license_plate:
                try:
                    reg = VehicleRegistration.objects.get(license_plate=instance.license_plate)
                    if reg.owner_phone_number:
                        sms_msg = (f"TRAFFIC ALERT: Violation recorded for {instance.license_plate}. "
                                   f"Speed: {instance.speed}km/h in {limit}km/h zone. "
                                   f"Ticket ID: {violation.id}. Fine: ${fine:.2f}")
                        send_sms_to_citizen.delay(reg.owner_phone_number, sms_msg)
                except VehicleRegistration.DoesNotExist:
                    logger.warning(f"No registration found for plate {instance.license_plate}")

    except Exception as e:
        logger.error(f"Error checking violations for Detection {instance.id}: {e}", exc_info=True)
