import boto3
from botocore.exceptions import ClientError
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class SMSService:
    """
    Service for sending SMS via AWS SNS
    """
    def __init__(self):
        self.sns_client = boto3.client(
            'sns',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_SNS_REGION_NAME
        )

    def send_sms(self, phone_number, message):
        try:
            response = self.sns_client.publish(
                PhoneNumber=phone_number,
                Message=message
            )
            return response['MessageId']
        except ClientError as e:
            logger.error(f"Failed to send SMS to {phone_number}: {e}")
            raise
