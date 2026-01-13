import boto3
from botocore.exceptions import ClientError
from django.conf import settings
from django.core.files.storage import default_storage
import logging

logger = logging.getLogger(__name__)

class AWSService:
    """
    Wrapper for AWS Services: SES (Email), SNS (SMS), S3 (Storage)
    """
    
    def __init__(self):
        self.ses_client = boto3.client(
            'ses',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_SES_REGION_NAME
        )
        self.sns_client = boto3.client(
            'sns',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_SNS_REGION_NAME
        )
        # S3 is largely handled by django-storages, but we might need direct access for specific operations
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME
        )

    def send_email(self, to_email, subject, body_html, body_text=None, source=None):
        """
        Send an email via AWS SES
        """
        if not source:
            source = settings.DEFAULT_FROM_EMAIL
            
        if not body_text:
            body_text = "Please view this email in a HTML-compatible mail client."

        try:
            response = self.ses_client.send_email(
                Source=source,
                Destination={
                    'ToAddresses': [to_email]
                },
                Message={
                    'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                    'Body': {
                        'Text': {'Data': body_text, 'Charset': 'UTF-8'},
                        'Html': {'Data': body_html, 'Charset': 'UTF-8'}
                    }
                }
            )
            return response['MessageId']
        except ClientError as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            raise

    def send_sms(self, phone_number, message):
        """
        Send SMS via AWS SNS
        """
        try:
            response = self.sns_client.publish(
                PhoneNumber=phone_number,
                Message=message
            )
            return response['MessageId']
        except ClientError as e:
            logger.error(f"Failed to send SMS to {phone_number}: {e}")
            raise
            
    def upload_file(self, file_obj, file_path):
        """
        Uploads a file to S3 using django-storages default storage
        """
        try:
            return default_storage.save(file_path, file_obj)
        except Exception as e:
             logger.error(f"Failed to upload file {file_path}: {e}")
             raise
