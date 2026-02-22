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

            # --- Deduplication Logic ---
            # 1. First, check if we have a license plate. If so, deduplicate by Plate + Patrol.
            # This ensures that even if a video loops or tracking IDs change, the same vehicle 
            # is updated rather than duplicated.
            license_plate = data.get('license_plate')
            frame_number = data.get('frame_number')
            track_id = data.get('track_id')

            if patrol and license_plate:
                # Try to find an existing detection for this vehicle in this patrol
                existing_detection = Detection.objects.filter(
                    patrol=patrol,
                    license_plate=license_plate
                ).first()

                if existing_detection:
                    # Update existing record with latest data
                    existing_detection.timestamp = timestamp
                    existing_detection.confidence = max(existing_detection.confidence, data.get('confidence', 0.0))
                    existing_detection.box_coordinates = data.get('box_coordinates', [])
                    existing_detection.speed = data.get('speed')
                    existing_detection.location = location
                    existing_detection.track_id = track_id
                    existing_detection.frame_number = frame_number or existing_detection.frame_number
                    existing_detection.save()
                    logger.debug(f"Updated record for plate {license_plate} (Patrol {patrol.id})")
                    return

            # 2. Fallback to Patrol + Frame + Track deduplication (existing logic)
            # This is for detections without plates or for fresh frames.
            if patrol and frame_number is not None:
                from django.db import IntegrityError
                try:
                    obj, created = Detection.objects.update_or_create(
                        patrol=patrol,
                        frame_number=frame_number,
                        drone=drone,
                        track_id=track_id,
                        defaults={
                            'timestamp': timestamp,
                            'vehicle_type': data.get('vehicle_type', 'unknown'),
                            'confidence': data.get('confidence', 0.0),
                            'box_coordinates': data.get('box_coordinates', []),
                            'license_plate': license_plate,
                            'speed': data.get('speed'),
                            'location': location,
                            'altitude': data.get('location', {}).get('altitude') if isinstance(data.get('location'), dict) else None
                        }
                    )
                    if created:
                        logger.info(f"Saved new detection for {drone_id} (Frame {frame_number})")
                    else:
                        logger.debug(f"Updated existing detection for {drone_id} (Frame {frame_number})")
                except IntegrityError:
                    logger.debug(f"Ignoring concurrent duplicate for {drone_id} (Frame {frame_number})")
            else:
                # Fallback for events without frame numbers or patrols
                Detection.objects.create(
                    drone=drone,
                    patrol=patrol,
                    timestamp=timestamp,
                    frame_number=frame_number or 0,
                    vehicle_type=data.get('vehicle_type', 'unknown'),
                    confidence=data.get('confidence', 0.0),
                    box_coordinates=data.get('box_coordinates', []),
                    license_plate=data.get('license_plate'),
                    speed=data.get('speed'),
                    track_id=data.get('track_id'),
                    location=location,
                    altitude=data.get('location', {}).get('altitude') if isinstance(data.get('location'), dict) else None
                )
                logger.info(f"Saved un-tracked detection for {drone_id}")
            
        except Exception as e:
            logger.error(f"Failed to save detection: {e}", exc_info=True)
