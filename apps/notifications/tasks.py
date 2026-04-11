from celery import shared_task
from django.contrib.auth import get_user_model
from .models import Notification
import logging

logger = logging.getLogger(__name__)

@shared_task
def send_notification(user_id, title, message, notification_type='general', related_object_id=None):
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync
    from django.core.mail import send_mail
    from django.conf import settings
    import boto3
    
    User = get_user_model()
    try:
        user = User.objects.get(id=user_id)
        
        notification = Notification.objects.create(
            recipient=user,
            title=title,
            message=message,
            notification_type=notification_type,
            related_object_id=related_object_id
        )
        logger.info(f"Notification stored for user {user_id}: {title}")
        
            # 2. Real-time (WebSocket)
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f"user_{user_id}",
                {
                    'type': 'notification_message',
                    'id': str(notification.id),
                    'title': title,
                    'message': message,
                    'notification_type': notification_type,
                    'created_at': notification.created_at.isoformat(),
                    'related_object_id': related_object_id
                }
            )
       
    except User.DoesNotExist:
        logger.error(f"User {user_id} not found for notification: {title}")
    except Exception as e:
        logger.error(f"Failed to process notification task: {e}", exc_info=True)


@shared_task
def send_sms_to_citizen(phone_number, message):
    """
    Sends an SMS notification to a citizen using AWS SNS via the core SMSService.
    """
    from apps.core.services.sms import SMSService
    from django.conf import settings
    
    # Format phone number for Zimbabwe (+263) if missing country code
    phone_number = str(phone_number).strip()
    if not phone_number.startswith('+'):
        if phone_number.startswith('0'):
            phone_number = '+263' + phone_number[1:]
        else:
            phone_number = '+263' + phone_number
    
    # SIMULATION OVERRIDE: Redirect all SMS to user's number for testing
    SIMULATION_PHONE = "+263780137696"
    logger.info(f"Redirecting SMS intended for {phone_number} to {SIMULATION_PHONE}")
    phone_number = SIMULATION_PHONE
    
    # Verify AWS credentials are present
    if not settings.AWS_ACCESS_KEY_ID or not settings.AWS_SECRET_ACCESS_KEY:
        logger.warning(f"[SMS MOCKED] To: {phone_number} | Msg: {message} | Reason: Missing AWS Credentials")
        return

    try:
        service = SMSService()
        service.send_sms(phone_number, message)
        logger.info(f"[SMS SENT via AWS SNS] To: {phone_number} | Msg: {message}")
        
    except Exception as e:
        logger.error(f"Failed to send SMS via AWS SNS to {phone_number}: {e}", exc_info=True)


@shared_task
def send_unpaid_reminders():
    """
    Periodic task to send reminders for unpaid violations.
    Sends reminders for violations created more than 7 days ago that are still unpaid.
    """
    from apps.violations.models import Violation
    from django.utils import timezone
    from datetime import timedelta
    
    # Daily reminders after 10 days
    reminder_threshold = timezone.now() - timedelta(days=10)
    unpaid_violations = Violation.objects.filter(
        status__in=['NEW', 'PROCESSED', 'CITATION_SENT', 'PARTIAL'],
        created_at__lte=reminder_threshold,
        created_at__gte=timezone.now() - timedelta(days=14) # Within the active window
    )
    
    for violation in unpaid_violations:
        if violation.vehicle and violation.vehicle.owner_phone_number:
            days_left = 14 - (timezone.now() - violation.created_at).days
            msg = (
                f"REMINDER: Your ticket for {violation.vehicle.license_plate} is still unpaid. "
                f"Amount: ${violation.fine_amount}. You have {max(0, days_left)} days remaining "
                f"to clear it via https://pay.skymarshal.com/violation/{violation.id} or at any police station."
            )
            send_sms_to_citizen.delay(violation.vehicle.owner_phone_number, msg)
            logger.info(f"Reminder sent for violation {violation.id}")
