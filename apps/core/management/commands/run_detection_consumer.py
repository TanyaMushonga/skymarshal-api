from django.core.management.base import BaseCommand
from django.conf import settings
from django.contrib.gis.geos import Point
from apps.detections.models import Detection
from apps.drones.models import Drone
from apps.core.kafka_config import get_kafka_consumer
import logging
import signal
import sys

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Runs the Kafka consumer for detection events'

    def handle(self, *args, **options):
        topic = settings.KAFKA_TOPICS['DETECTIONS']
        
        logger.info(f"Starting Detection Consumer on topic: {topic}")
        
        # Use Factory from core config
        consumer = get_kafka_consumer(
            topic=topic, 
            group_id='skymarshal_detection_group'
        )
        
        # Handle graceful shutdown
        def signal_handler(sig, frame):
            logger.info('Stopping Detection Consumer...')
            consumer.close()
            sys.exit(0)
            
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        for message in consumer:
            try:
                data = message.value
                self.process_message(data)
            except Exception as e:
                logger.error(f"Error processing message: {e}", exc_info=True)

    def process_message(self, data):
        """
        Create a Detection record from the message data
        """
        try:
            drone_id = data.get('drone_id')
            timestamp = data.get('timestamp')
            
            # Find the drone
            try:
                drone = Drone.objects.get(drone_id=drone_id)
            except Drone.DoesNotExist:
                logger.warning(f"Drone ID {drone_id} not found. Skipping detection.")
                return
            
            # Create Point for location
            location = None
            if 'location' in data and data['location']:
                lat = data['location'].get('latitude')
                lon = data['location'].get('longitude')
                if lat is not None and lon is not None:
                    location = Point(lon, lat)

            Detection.objects.create(
                drone=drone,
                timestamp=timestamp,
                frame_number=data.get('frame_number'),
                vehicle_type=data.get('vehicle_type', 'unknown'),
                confidence=data.get('confidence', 0.0),
                box_coordinates=data.get('box_coordinates', []),
                license_plate=data.get('license_plate'),
                speed=data.get('speed'),
                location=location,
                altitude=data.get('location', {}).get('altitude')
            )
            
            logger.info(f"Saved detection for {drone_id} (Frame {data.get('frame_number')})")
            
        except Exception as e:
            logger.error(f"Failed to save detection: {e}", exc_info=True)
