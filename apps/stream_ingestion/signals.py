from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from .models import VideoStream, StreamSession
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=VideoStream)
def log_stream_created(sender, instance, created, **kwargs):
    """
    Log when new stream is created
    
    Logic:
    - If created=True, log info with stream_id and drone name
    """
    if created:
        logger.info(
            f"New video stream created: {instance.stream_id} "
            f"for drone {instance.drone.drone_id} ({instance.drone.name})"
        )


@receiver(pre_delete, sender=VideoStream)
def ensure_stream_stopped(sender, instance, **kwargs):
    """
    Ensure stream is stopped before deletion
    
    Logic:
    - If instance.is_active=True:
      - Log warning
      - Set is_active=False
      - Save instance
      - Close any active sessions
    """
    if instance.is_active:
        logger.warning(
            f"Deleting active stream {instance.stream_id} - forcing stop"
        )
        instance.is_active = False
        instance.save()
        
        # Close active sessions
        active_sessions = instance.sessions.filter(end_time__isnull=True)
        for session in active_sessions:
            from django.utils import timezone
            session.end_time = timezone.now()
            session.save()


@receiver(post_save, sender=StreamSession)
def log_session_events(sender, instance, created, **kwargs):
    """
    Log session lifecycle events
    
    Logic:
    - If created=True: Log session started
    - If end_time changed from None to a value: Log session ended with stats
    """
    if created:
        logger.info(
            f"Stream session started: {instance.id} "
            f"for stream {instance.stream.stream_id}"
        )
    else:
        # Check if end_time was just set
        if instance.end_time:
            duration = (instance.end_time - instance.start_time).total_seconds()
            fps = instance.frames_processed / duration if duration > 0 else 0
            logger.info(
                f"Stream session ended: {instance.id}, "
                f"Frames: {instance.frames_processed}, "
                f"Duration: {duration:.2f}s, "
                f"FPS: {fps:.2f}"
            )
