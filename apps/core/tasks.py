from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

@shared_task
def send_email_task(recipient, subject, message, html_message=None):
    """Send email notification"""
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            html_message=html_message,
            fail_silently=False
        )
        logger.info(f"Email sent to {recipient}: {subject}")
    except Exception as e:
        logger.error(f"Failed to send email to {recipient}: {e}")

@shared_task
def send_sms_task(phone_number, message):
    """Send SMS notification"""
    try:
        # This is a placeholder - integrate with actual SMS service like Twilio
        # For now, just log the SMS
        logger.info(f"SMS to {phone_number}: {message}")
        
        # Example Twilio integration:
        # from twilio.rest import Client
        # client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        # client.messages.create(
        #     body=message,
        #     from_=settings.TWILIO_PHONE_NUMBER,
        #     to=phone_number
        # )
        
    except Exception as e:
        logger.error(f"Failed to send SMS to {phone_number}: {e}")