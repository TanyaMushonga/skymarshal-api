import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')

app = Celery('api')

app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Periodic tasks
app.conf.beat_schedule = {
    'aggregate-metrics-every-5min': {
        'task': 'apps.analytics.tasks.aggregate_traffic_metrics',
        'schedule': crontab(minute='*/5'),
    },
    'generate-hourly-heatmaps': {
        'task': 'apps.analytics.tasks.generate_heat_map',
        'schedule': crontab(minute=0),
    },
    'monitor-drone-health': {
        'task': 'apps.drones.tasks.monitor_drone_health',
        'schedule': 60.0,
    },
    'cleanup-old-sessions': {
        'task': 'apps.stream_ingestion.tasks.cleanup_old_sessions',
        'schedule': crontab(minute='*/30'),  # Every 30 minutes
    },
    'monitor-stream-health': {
        'task': 'apps.stream_ingestion.tasks.monitor_stream_health',
        'schedule': 120.0,  # Every 2 minutes
    },
}

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
