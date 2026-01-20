from django.apps import AppConfig

class StreamIngestionConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.stream_ingestion'
    verbose_name = 'Stream Ingestion'
    
    def ready(self):
        """Import signals when app is ready"""
        import apps.stream_ingestion.signals