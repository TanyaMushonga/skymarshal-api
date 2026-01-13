from celery import shared_task
from apps.core.services import AWSService
import logging

logger = logging.getLogger(__name__)

@shared_task
def send_email_task(to_email, subject, body_html, body_text=None):
    """
    Celery task to send email via AWS SES
    """
    aws_service = AWSService()
    try:
        aws_service.send_email(to_email, subject, body_html, body_text)
        logger.info(f"Email sent to {to_email}")
    except Exception as e:
        logger.error(f"Failed to send email task: {e}")

@shared_task
def send_sms_task(phone_number, message):
    """
    Celery task to send SMS via AWS SNS
    """
    aws_service = AWSService()
    try:
        aws_service.send_sms(phone_number, message)
        logger.info(f"SMS sent to {phone_number}")
    except Exception as e:
        logger.error(f"Failed to send SMS task: {e}")
