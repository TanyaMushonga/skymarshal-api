from django.core.management.base import BaseCommand, CommandError
from apps.drones.models import Drone, DroneAPIKey

class Command(BaseCommand):
    help = 'Generate or retrieve API key for a drone'
    
    def add_arguments(self, parser):
        parser.add_argument('drone_id', type=str, help='Drone ID (e.g., DRONE_001)')
        parser.add_argument(
            '--regenerate',
            action='store_true',
            help='Regenerate key if already exists'
        )
    
    def handle(self, *args, **options):
        drone_id = options['drone_id']
        regenerate = options['regenerate']
        
        try:
            drone = Drone.objects.get(drone_id=drone_id)
        except Drone.DoesNotExist:
            raise CommandError(f'Drone "{drone_id}" does not exist')
            
        if regenerate:
            if hasattr(drone, 'api_key'):
                try:
                    drone.api_key.delete()
                    self.stdout.write(self.style.WARNING(f'Deleted existing key for {drone_id}'))
                except Exception:
                    pass
            
        api_key, created = DroneAPIKey.objects.get_or_create(drone=drone)
        
        if created:
             self.stdout.write(self.style.SUCCESS(f'Created new key for {drone_id}'))
        else:
             self.stdout.write(f'Retrieved existing key for {drone_id}')
             
        self.stdout.write(f'\nAPI Key for {drone_id}:')
        self.stdout.write(self.style.SUCCESS(api_key.key))
        
        self.stdout.write(self.style.WARNING('\n⚠ SECURITY WARNING: Store this key securely!'))
        self.stdout.write(self.style.WARNING('This key provides full access for this drone.'))
