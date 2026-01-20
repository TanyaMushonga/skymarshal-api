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
