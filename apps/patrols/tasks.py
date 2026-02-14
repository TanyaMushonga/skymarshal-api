from celery import shared_task
from django.utils import timezone
from datetime import timedelta
import logging
from .models import Patrol
from .services import PatrolService

logger = logging.getLogger(__name__)

@shared_task
def cap_overlong_patrols():
    """
    Task to automatically terminate patrols that have been active for more than 12 hours.
    Runs periodically to ensure system resources are released.
    """
    threshold_time = timezone.now() - timedelta(hours=12)
    
    # Filter for patrols that are still ACTIVE and started more than 12 hours ago
    overlong_patrols = Patrol.objects.filter(
        status='ACTIVE',
        start_time__lt=threshold_time
    )
    
    count = overlong_patrols.count()
    
    if count == 0:
        logger.info("No overlong patrols found to cap.")
        return 0

    logger.info(f"Found {count} overlong patrols. Proceeding to cap them.")
    
    for patrol in overlong_patrols:
        try:
            # Terminate the patrol
            patrol.status = 'COMPLETED'
            patrol.end_time = timezone.now()
            patrol.save()
            
            # Toggle officer off-duty
            officer = patrol.officer
            officer.is_on_duty = False
            officer.save(update_fields=['is_on_duty'])
            
            # Clear drone cache to reflect the state change in the UI/Services
            PatrolService.clear_cache(patrol.drone.drone_id)
            
            logger.info(f"Capped patrol {patrol.id} for drone {patrol.drone.drone_id} and toggled officer {officer.email} off-duty")
            
        except Exception as e:
            logger.error(f"Failed to cap patrol {patrol.id}: {str(e)}")

    return count
