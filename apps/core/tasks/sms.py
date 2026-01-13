from celery import shared_task
from apps.core.services.sms import SMSService
import logging

logger = logging.getLogger(__name__)

@shared_task
def send_sms_task(phone_number, message):
    """
    Celery task to send SMS via AWS SNS
    """
    service = SMSService()
    try:
        service.send_sms(phone_number, message)
        logger.info(f"SMS sent to {phone_number}")
    except Exception as e:
        logger.error(f"Failed to send SMS task: {e}")
