import boto3
from django.conf import settings
from django.core.files.storage import default_storage
import logging

logger = logging.getLogger(__name__)

class StorageService:
    """
    Service for file storage operations via S3 (or default storage)
    """
    def __init__(self):
         # S3 is largely handled by django-storages, but we might need direct access for specific operations
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME
        )

    def upload_file(self, file_obj, file_path):
        """
        Uploads a file to S3 using django-storages default storage
        """
        try:
            return default_storage.save(file_path, file_obj)
        except Exception as e:
             logger.error(f"Failed to upload file {file_path}: {e}")
             raise
