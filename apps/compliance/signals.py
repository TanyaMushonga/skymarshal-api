from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.detections.models import Detection
from apps.vehicle_lookup.models import VehicleRegistration
from .models import ComplianceScore
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Detection)
def record_compliant_behavior(sender, instance, created, **kwargs):
    """
    If a vehicle is detected driving safely (under limit), award points.
    Prerequisite: Vehicle must be registered in lookup system.
    """
    if not created:
        return
        
    try:
        # 1. Check if License Plate exists
        if not instance.license_plate:
            return

        # 2. Get Limit
        limit = 60.0
        if instance.patrol and instance.patrol.patrol_config:
            limit = float(instance.patrol.patrol_config.get('speed_limit', 60.0))
        elif hasattr(instance.drone, 'speed_limit'):
            limit = instance.drone.speed_limit

        # 3. Check Compliance
        # We allow a small buffer or strictly under limit. Let's say strictly <= limit.
        if instance.speed and instance.speed <= limit:
            try:
                vehicle = VehicleRegistration.objects.get(license_plate=instance.license_plate)
                
                score, _ = ComplianceScore.objects.get_or_create(vehicle=vehicle)
                # Simple logic: 1 point per compliant detection
                # In real world, might limit frequency (e.g. 1 point per hour)
                score.safe_driving_points += 1
                score.save()
                
                # logger.debug(f"Awarded compliance point to {vehicle.license_plate}")
                
            except VehicleRegistration.DoesNotExist:
                # Unregistered vehicle, ignore
                pass
                
    except Exception as e:
        logger.error(f"Error recording compliance for {instance.id}: {e}")
