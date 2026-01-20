import os
import sys
import logging
import time
import django

# Setup Django environment BEFORE other imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) # Add project root to path
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "api.settings")
django.setup()

from django.conf import settings
from apps.core.kafka_config import get_kafka_producer, get_kafka_consumer
from computer_vision.src.detector import VehicleDetector
from computer_vision.src.processor import VideoProcessor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """
    Main entry point for the SkyMarshal IATOS project.
    Can run in 'stream' mode (Kafka) or 'file' mode (local video).
    """
    mode = os.environ.get('CV_MODE', 'stream') # Default to stream
    
    detector = VehicleDetector()
    processor = VideoProcessor(detector)
    
    if mode == 'file':
        video_path = 'traffic_sample.mp4'
        if os.path.exists(video_path):
            processor.process_video(video_path)
        else:
            logger.warning(f"File {video_path} not found.")
    else:
        logger.info("Starting CV in STREAM mode...")
        
        # Kafka Configuration from Django Settings
        input_topic = settings.KAFKA_TOPICS['RAW_FRAMES']
        output_topic = settings.KAFKA_TOPICS['DETECTIONS']
        
        try:
            # Use Core Producer Singleton
            producer = get_kafka_producer()
            
            # Use Core Consumer Factory
            consumer = get_kafka_consumer(
                topic=input_topic,
                group_id='cv_processor_group'
            )
            logger.info(f"Listening for frames on {input_topic}...")
            
            for message in consumer:
                try:
                    data = message.value
                    stream_id = data.get('stream_id')
                    frame_number = data.get('frame_number')
                    frame_data = data.get('frame_data')
                    frame_rate = data.get('frame_rate', 30.0)
                    gps = data.get('gps', {})
                    
                    if not frame_data:
                        continue
                        
                    # Process frame
                    detections = processor.process_frame_data(frame_data, frame_number, frame_rate)
                    
                    # Publish detections
                    for det in detections:
                        event = {
                            'drone_id': data.get('drone_id'),
                            'stream_id': stream_id,
                            'timestamp': data.get('timestamp'),
                            'frame_number': frame_number,
                            'vehicle_type': det['vehicle_type'],
                            'confidence': float(det['confidence']),
                            'box_coordinates': det['box_coordinates'],
                            'license_plate': det['license_plate'],
                            'speed': det['speed'],
                            'location': gps 
                        }
                        # Use the core producer's send method
                        producer.send(output_topic, event)
                        
                except Exception as e:
                    logger.error(f"Error processing frame: {e}")
                    
        except Exception as e:
            logger.error(f"Critical Kafka Error: {e}")
            # Add backoff/retry logic or exit
            time.sleep(5)

if __name__ == "__main__":
    main()
