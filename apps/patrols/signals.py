import json
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Patrol
from apps.stream_ingestion.models import VideoStream
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Patrol)
def handle_patrol_stream_automation(sender, instance, created, **kwargs):
    """
    Automate stream start/stop based on patrol status changes.
    - When a patrol is created (ACTIVE): notify the drone's channel group to start streaming.
    - When a patrol is COMPLETED/CANCELLED: stop any active streams for that drone.
    """
    drone = instance.drone
    stream = VideoStream.objects.filter(drone=drone).first()

    if created and instance.status == 'ACTIVE':
        if stream:
            # Notify the ESP32 via its dedicated drone channel group to start streaming
            # The ESP32 must be connected to the 'drone_<drone_id>' group to receive this.
            try:
                from asgiref.sync import async_to_sync
                from channels.layers import get_channel_layer

                channel_layer = get_channel_layer()
                drone_group_name = f"drone_{drone.drone_id}"

                async_to_sync(channel_layer.group_send)(
                    drone_group_name,
                    {
                        'type': 'patrol_started',
                        'patrol_id': instance.id,
                        'stream_id': str(stream.stream_id),
                        'drone_id': drone.drone_id,
                    }
                )
                logger.info(
                    f"Signal: Sent 'patrol_started' command to drone group '{drone_group_name}' "
                    f"for patrol {instance.id}"
                )
            except Exception as e:
                logger.error(f"Signal: Failed to send patrol_started command to drone: {e}")

    elif not created and instance.status in ['COMPLETED', 'CANCELLED']:
        # Stop active streams for this drone
        active_streams = VideoStream.objects.filter(drone=drone, is_active=True)
        for s in active_streams:
            s.is_active = False
            s.save(update_fields=['is_active'])
            logger.info(f"Signal: Stopped stream {s.stream_id} as patrol {instance.id} {instance.status}")

            # Notify the drone to stop streaming
            try:
                from asgiref.sync import async_to_sync
                from channels.layers import get_channel_layer

                channel_layer = get_channel_layer()
                drone_group_name = f"drone_{drone.drone_id}"

                async_to_sync(channel_layer.group_send)(
                    drone_group_name,
                    {
                        'type': 'patrol_ended',
                        'patrol_id': instance.id,
                        'drone_id': drone.drone_id,
                    }
                )
                logger.info(f"Signal: Sent 'patrol_ended' command to drone group '{drone_group_name}'")
            except Exception as e:
                logger.error(f"Signal: Failed to send patrol_ended command to drone: {e}")
