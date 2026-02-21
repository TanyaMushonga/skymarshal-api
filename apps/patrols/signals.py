from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Patrol
from apps.stream_ingestion.models import VideoStream
from apps.stream_ingestion.tasks import simulate_stream_task
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Patrol)
def handle_patrol_stream_automation(sender, instance, created, **kwargs):
    """
    Automate stream start/stop based on patrol status changes.
    """
    drone = instance.drone
    
    if created and instance.status == 'ACTIVE':
        # Automatically start stream if it exists
        stream = VideoStream.objects.filter(drone=drone).first()
        if stream:
            simulate_stream_task.delay(
                stream_id=stream.id,
                patrol_id=instance.id,
                video_file='computer_vision/car_detection.mp4'
            )
            logger.info(f"Signal: Automatically started stream simulation (car_detection.mp4) for patrol {instance.id}")
            
    elif not created:
        if instance.status in ['COMPLETED', 'CANCELLED']:
            # Automatically stop active streams for this drone
            active_streams = VideoStream.objects.filter(drone=drone, is_active=True)
            for stream in active_streams:
                stream.is_active = False
                stream.save(update_fields=['is_active'])
                logger.info(f"Signal: Stopped stream {stream.stream_id} as patrol {instance.id} {instance.status}")
