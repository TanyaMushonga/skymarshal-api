from django.apps import AppConfig

class ViolationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.violations'

    def ready(self):
        import apps.violations.signals
