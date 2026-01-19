from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Drone, DroneAPIKey
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Drone)
def create_api_key_for_drone(sender, instance, created, **kwargs):

    if created:
        api_key = DroneAPIKey.objects.create(drone=instance)
        logger.info(f"Generated API key for new drone: {instance.drone_id}")
