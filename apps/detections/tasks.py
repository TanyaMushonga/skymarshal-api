from celery import shared_task
import logging
from .models import Detection

logger = logging.getLogger(__name__)

@shared_task
def cleanup_old_detections():
    """
    Delete old detections if the total count exceeds 100.
    """
    try:
        max_detections = 100
        count = Detection.objects.count()
        
        if count > max_detections:
            # Find the IDs of the 100 most recent detections
            latest_ids = Detection.objects.order_by('-timestamp').values_list('id', flat=True)[:max_detections]
            
            # Delete everything else
            deleted_count, _ = Detection.objects.exclude(id__in=latest_ids).delete()
            
            logger.info(f"Cleanup: Deleted {deleted_count} old detections to maintain limit of {max_detections}")
            return f"Deleted {deleted_count} records"
            
        return "No cleanup needed"
    except Exception as e:
        logger.error(f"Error in cleanup_old_detections: {e}", exc_info=True)
        return str(e)
