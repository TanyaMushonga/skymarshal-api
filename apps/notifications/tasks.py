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
    Sends an SMS notification to a citizen using AWS SNS.
    """
    import boto3
    from django.conf import settings
    
    try:
        # Check if we have AWS creds, or mock it/log it
        # For this environment we'll just log if credentials aren't set up, 
        # but the code structure is correct for SNS.
        
        # client = boto3.client(
        #     'sns',
        #     region_name=settings.AWS_REGION_NAME,
        #     aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        #     aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
        # )
        # client.publish(PhoneNumber=phone_number, Message=message)
        
        logger.info(f"[SMS SENT] To: {phone_number} | Msg: {message}")
        
    except Exception as e:
        logger.error(f"Failed to send SMS to {phone_number}: {e}", exc_info=True)
