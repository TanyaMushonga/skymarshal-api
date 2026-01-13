import boto3
from botocore.exceptions import ClientError
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class EmailService:
    """
    Service for sending emails via AWS SES
    """
    def __init__(self):
        self.ses_client = boto3.client(
            'ses',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_SES_REGION_NAME
        )

    def send_email(self, to_email, subject, body_html, body_text=None, source=None):
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
