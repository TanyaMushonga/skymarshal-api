from django.core.management.base import BaseCommand
from apps.drones.models import Drone
from apps.stream_ingestion.models import VideoStream, StreamSession
from apps.patrols.models import Patrol
from django.utils import timezone
import random

class Command(BaseCommand):
    help = 'Seeds the database with dummy video streams and sessions for drones'

    def handle(self, *args, **options):
        self.stdout.write('Seeding video streams and sessions...')

        # Ensure we have drones
        if Drone.objects.count() == 0:
            self.stdout.write('No drones found. Creating sample drones first...')
            drones_data = [
                {'id': 'DR-001', 'name': 'Phantom Scout', 'model': 'DJI Phantom 4', 'serial': 'P4-123456'},
                {'id': 'DR-002', 'name': 'Mavic Patrol', 'model': 'DJI Mavic 3', 'serial': 'M3-789012'},
                {'id': 'DR-003', 'name': 'Matrice Heavy', 'model': 'DJI Matrice 300', 'serial': 'M300-345678'},
            ]
            
            for d in drones_data:
                Drone.objects.create(
                    drone_id=d['id'],
                    name=d['name'],
                    model=d['model'],
                    serial_number=d['serial'],
                    is_active=True
                )
            self.stdout.write(f'Created {len(drones_data)} drones.')

        drones = Drone.objects.all()
        
        streams_created = 0
        sessions_created = 0

        for drone in drones:
            # 1. Create or Get Stream
            stream, created = VideoStream.objects.get_or_create(
                drone=drone,
                defaults={
                    'rtsp_url': f"rtsp://192.168.1.{random.randint(100, 200)}:554/stream1",
                    'is_active': True,
                    'frame_rate': 30,
                    'resolution': '1920x1080'
                }
            )
            
            if created:
                streams_created += 1
                self.stdout.write(f'Created stream for {drone.name}')
            
            # 2. Create Active Stream Session
            # Try to find an active patrol for this drone
            active_patrol = Patrol.objects.filter(drone=drone, status='ACTIVE').first()
            
            # If no active patrol, check for any patrol, or skip linking
            patrol = active_patrol or Patrol.objects.filter(drone=drone).first()
            
            if not StreamSession.objects.filter(stream=stream, end_time__isnull=True).exists():
                session = StreamSession.objects.create(
                    stream=stream,
                    patrol=patrol,
                    start_time=timezone.now(),
                    kafka_topic=f"drone-stream-{drone.drone_id.lower()}",
                    frames_processed=random.randint(0, 1000)
                )
                sessions_created += 1
                self.stdout.write(f'Created active session for stream {stream.stream_id}')

        self.stdout.write(self.style.SUCCESS(f'Successfully seeded {streams_created} streams and {sessions_created} sessions'))
