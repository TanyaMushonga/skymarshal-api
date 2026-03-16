from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Drone, DroneAPIKey
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Drone)
def create_related_objects_for_drone(sender, instance, created, **kwargs):
    """
    Automatically create API Key and VideoStream for new drones.
    """
    if created:
        # Create API key
        api_key = DroneAPIKey.objects.create(drone=instance, name="Primary ESP32 Key")
        
        # Create VideoStream
        try:
            from apps.stream_ingestion.models import VideoStream
            VideoStream.objects.create(
                drone=instance,
                resolution="1920x1080",
                frame_rate=30
            )
            logger.info(f"Automatically created API key and VideoStream for drone: {instance.drone_id}")
        except ImportError:
            logger.error("Could not import VideoStream from apps.stream_ingestion.models")
        except Exception as e:
            logger.error(f"Error creating VideoStream for drone: {e}")
