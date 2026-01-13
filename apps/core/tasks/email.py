from celery import shared_task
from apps.core.services.email import EmailService
import logging

logger = logging.getLogger(__name__)

@shared_task
def send_email_task(to_email, subject, body_html, body_text=None):
    """
    Celery task to send email via AWS SES
    """
    service = EmailService()
    try:
        service.send_email(to_email, subject, body_html, body_text)
        logger.info(f"Email sent to {to_email}")
    except Exception as e:
        logger.error(f"Failed to send email task: {e}")
