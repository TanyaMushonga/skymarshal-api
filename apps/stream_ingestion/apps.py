from django.apps import AppConfig


class StreamIngestionConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.stream_ingestion'

    def ready(self):
        import apps.stream_ingestion.signals  # noqa