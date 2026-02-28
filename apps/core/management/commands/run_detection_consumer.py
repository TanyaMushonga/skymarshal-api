from django.core.management.base import BaseCommand
from django.conf import settings
from django.contrib.gis.geos import Point
from apps.detections.models import Detection
from apps.drones.models import Drone
from apps.core.kafka_config import get_kafka_consumer
from apps.patrols.services import PatrolService
import logging
import signal
import sys
import datetime
from django.utils.dateparse import parse_datetime
import base64
from django.core.files.base import ContentFile

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
            timestamp_raw = data.get('timestamp')
            
            # Robust timestamp parsing
            if isinstance(timestamp_raw, (int, float)):
                timestamp = datetime.datetime.fromtimestamp(timestamp_raw, tz=datetime.timezone.utc)
            elif isinstance(timestamp_raw, str):
                timestamp = parse_datetime(timestamp_raw)
            else:
                timestamp = datetime.datetime.now(datetime.timezone.utc)
            
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

            # Retrieve active patrol
            patrol = PatrolService.get_active_patrol(drone_id)

            # --- Extract track info early for image naming ---
            track_id = data.get('track_id')
            confidence = data.get('confidence', 0.0)
            speed = data.get('speed')
            license_plate = data.get('license_plate') or 'UNKNOWN-PLATE'
            frame_number = data.get('frame_number')

            # --- Prepare image if provided ---
            image_file = None
            frame_data = data.get('frame_data')
            if frame_data:
                try:
                    format, imgstr = frame_data.split(';base64,') if ';base64,' in frame_data else (None, frame_data)
                    ext = format.split('/')[-1] if format else 'jpg'
                    filename = f"det_{drone_id}_{track_id}_{int(timestamp.timestamp())}.{ext}"
                    image_file = ContentFile(base64.b64decode(imgstr), name=filename)
                except Exception as img_err:
                    logger.error(f"Failed to prepare detection image: {img_err}")

            # --- Strict Filtering Logic ---
            # 1. Ignore low confidence (below 60%)
            if confidence < 0.6:
                logger.debug(f"Ignoring low confidence detection ({confidence:.2f}) for track {track_id}")
                return

            # 2. Ignore missing speeds (but allow 0km/h for stopped/stabilizing vehicles)
            if speed is None:
                logger.debug(f"Ignoring detection without valid speed ({speed}) for track {track_id}")
                return

            if license_plate is None or license_plate == "" or license_plate == "Scanning..." or license_plate == "None":
                license_plate = "UNKNOWN-PLATE"

            # Standardized update_or_create based on track-level uniqueness
            from django.db import IntegrityError
            try:
                obj, created = Detection.objects.update_or_create(
                    drone=drone,
                    track_id=track_id,
                    patrol=patrol,
                    defaults={
                        'timestamp': timestamp,
                        'frame_number': frame_number or 0,
                        'vehicle_type': data.get('vehicle_type', 'unknown'),
                        'confidence': confidence,
                        'box_coordinates': data.get('box_coordinates', []),
                        'license_plate': license_plate,
                        'speed': speed,
                        'location': location,
                        'altitude': data.get('location', {}).get('altitude') if isinstance(data.get('location'), dict) else None,
                        'image_snapshot': image_file
                    }
                )
                
                if created:
                    logger.info(f"New track {track_id} detected for {drone_id}")
                else:
                    logger.debug(f"Updated track {track_id} info for {drone_id}")
                    
            except IntegrityError:
                logger.warning(f"Integrity error for track {track_id} on {drone_id}. Skipping.")
            
        except Exception as e:
            logger.error(f"Failed to save detection: {e}", exc_info=True)
