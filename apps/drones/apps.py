from django.apps import AppConfig

class DronesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.drones'
    
    def ready(self):
        import apps.drones.signals
