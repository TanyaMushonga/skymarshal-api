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
    CV_DIR = os.path.dirname(os.path.abspath(__file__))
    mode = os.environ.get('CV_MODE', 'stream') # Default to stream
    
    detector = VehicleDetector(model_name=os.path.join(CV_DIR, 'yolov8n.pt'))
    processor = VideoProcessor(detector)
    
    if mode == 'file':
        video_path = os.path.join(CV_DIR, 'traffic_sample.mp4')
        if os.path.exists(video_path):
            processor.process_video(video_path)
        else:
            logger.warning(f"File {video_path} not found.")
    else:
        logger.info("Starting CV in STREAM mode...")
        
        # Kafka Configuration from Django Settings
        input_topic = settings.KAFKA_TOPICS['RAW_FRAMES']
        output_topic = settings.KAFKA_TOPICS['DETECTIONS']
        processed_topic = settings.KAFKA_TOPICS.get('PROCESSED_FRAMES', 'processed_frames')
        
        try:
            # Use Core Producer Singleton
            producer = get_kafka_producer()
            
            # Use Core Consumer Factory
            consumer = get_kafka_consumer(
                topic=input_topic,
                group_id='cv_processor_group_v7'
            )
            logger.info(f"Listening for frames on {input_topic}...")
            
            for message in consumer:
                try:
                    data = message.value
                    if not data:
                        continue
                        
                    frame_data = data.get('frame_data')
                    frame_number = data.get('frame_number')
                    frame_rate = data.get('frame_rate', 30)
                    stream_id = data.get('stream_id')
                    patrol_id = data.get('patrol_id')
                    gps = data.get('location')

                    if not frame_data:
                        continue
                        
                    # Check if source matches stream mode (with caching to avoid excess DB hits)
                    from apps.stream_ingestion.models import VideoStream
                    current_time = time.time()
                    
                    # Global cache for modes
                    if not hasattr(main, 'mode_cache'):
                        main.mode_cache = {}
                        main.last_check = {}
                    
                    cached_mode = main.mode_cache.get(stream_id)
                    last_check = main.last_check.get(stream_id, 0)
                    
                    if not cached_mode or current_time - last_check > 5:
                        try:
                            stream = VideoStream.objects.get(stream_id=stream_id)
                            cached_mode = stream.stream_mode
                            main.mode_cache[stream_id] = cached_mode
                            main.last_check[stream_id] = current_time
                        except Exception:
                            # If stream not found, default to processing for now or skip
                            pass
                    
                    incoming_source = data.get('source', 'LIVE') # Default to LIVE for backward compatibility
                    if cached_mode and incoming_source != cached_mode:
                        logger.debug(f"Dropping {incoming_source} frame for stream {stream_id} (active: {cached_mode})")
                        continue
                        
                    # Process frame
                    try:
                        logger.info(f"Consumed frame {frame_number} from stream {stream_id}")
                        start_time = time.time()
                        detections, annotated_frame = processor.process_frame_data(
                            frame_data, frame_number, frame_rate, annotate=True, mode=cached_mode
                        )
                        process_time = time.time() - start_time
                        
                        logger.info(f"Processed frame {frame_number} in {process_time:.3f}s. Found {len(detections)} detections.")
                        
                        # Publish detections
                        for det in detections:
                            event = {
                                'drone_id': data.get('drone_id'),
                                'stream_id': stream_id,
                                'patrol_id': patrol_id,
                                'timestamp': data.get('timestamp'),
                                'frame_number': frame_number,
                                'vehicle_type': det['vehicle_type'],
                                'confidence': float(det['confidence']),
                                'box_coordinates': det['box_coordinates'],
                                'license_plate': det['license_plate'],
                                'speed': det['speed'],
                                'track_id': det.get('track_id'),
                                'location': gps,
                                'frame_data': annotated_frame, # Send for evidence capture
                                'source': cached_mode
                            }
                            producer.send(output_topic, event)
                            logger.info(f"Sent detection for frame {frame_number} to {output_topic} (patrol: {patrol_id})")

                        # Publish annotated frame for live viewing
                        # Publish annotated frame for live viewing
                        if annotated_frame:
                            frame_event = {
                                'drone_id': data.get('drone_id'),
                                'stream_id': stream_id,
                                'patrol_id': patrol_id,
                                'timestamp': data.get('timestamp'),
                                'frame_number': frame_number,
                                'frame_data': annotated_frame,
                                'source': cached_mode
                            }
                            producer.send(processed_topic, frame_event)
                            
                            if frame_number % 10 == 0:
                                logger.info(f"CV Processor: Successfully published annotated frame {frame_number} for stream {stream_id}")
                            
                    except Exception as e:
                        logger.error(f"Error processing frame {frame_number}: {e}", exc_info=True)
                        
                except Exception as e:
                    logger.error(f"Error in consumer loop: {e}", exc_info=True)
                    
        except Exception as e:
            logger.error(f"Critical Kafka Error: {e}")
            # Add backoff/retry logic or exit
            time.sleep(5)

if __name__ == "__main__":
    main()
