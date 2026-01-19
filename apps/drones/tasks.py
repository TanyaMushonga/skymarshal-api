from celery import shared_task
from .models import DroneAPIKey

@shared_task
def record_api_key_usage(api_key_id):

    try:
        api_key = DroneAPIKey.objects.get(id=api_key_id)
        api_key.record_usage()
    except DroneAPIKey.DoesNotExist:
        pass