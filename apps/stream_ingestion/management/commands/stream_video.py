import cv2
import base64
import time
from django.utils import timezone
import logging
from django.core.management.base import BaseCommand
from django.conf import settings
from apps.core.kafka_config import get_kafka_producer
from apps.drones.models import Drone

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Streams a video file to Kafka as individual frames'

    def add_arguments(self, parser):
        parser.add_argument('--file', type=str, required=True, help='Path to the video file')
        parser.add_argument('--drone_id', type=str, default='DRONE-001', help='Drone ID to associate with the stream')
        parser.add_argument('--stream_id', type=str, default='STREAM-TEST', help='Stream ID')
        parser.add_argument('--loop', action='store_true', help='Loop the video continuously')

    def handle(self, *args, **options):
        video_path = options['file']
        drone_id = options['drone_id']
        stream_id = options['stream_id']
        loop = options['loop']
        
        # Verify drone exists or create a mock one if needed
        drone, _ = Drone.objects.get_or_create(
            drone_id=drone_id,
            defaults={'name': 'Mock Test Drone', 'model': 'Simulator'}
        )

        producer = get_kafka_producer()
        topic = settings.KAFKA_TOPICS['RAW_FRAMES']
        
        logger.info(f"Starting stream for {video_path} to topic {topic}")

        while True:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                self.stderr.write(f"Error: Could not open video {video_path}")
                return

            fps = cap.get(cv2.CAP_PROP_FPS)
            if fps <= 0: fps = 30.0
            delay = 1.0 / fps

            frame_number = 0
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break

                # Encode frame to JPEG then Base64
                _, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                frame_data = base64.b64encode(buffer).decode('utf-8')

                payload = {
                    'drone_id': drone_id,
                    'stream_id': stream_id,
                    'timestamp': timezone.now().isoformat(),
                    'frame_number': frame_number,
                    'frame_data': frame_data,
                    'frame_rate': fps,
                    'gps': {'latitude': -17.8252, 'longitude': 31.0335, 'altitude': 50.0} # Harara Mock GPS
                }

                producer.send(topic, payload)
                
                if frame_number % 100 == 0:
                    logger.info(f"Streamed frame {frame_number}")

                frame_number += 1
                time.sleep(delay)

            cap.release()
            if not loop:
                break
            logger.info("Restarting video loop...")

        logger.info("Streaming complete.")
