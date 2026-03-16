from celery import shared_task
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import cv2
import base64
import logging
from .models import VideoStream, StreamSession
from apps.core.kafka_config import get_kafka_producer
from apps.drones.models import GPSLocation
from apps.patrols.services import PatrolService

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def process_rtsp_stream(self, stream_id):
       
    try:
        stream = VideoStream.objects.select_related('drone').get(stream_id=stream_id)
        logger.info(f"Starting stream processing: {stream_id}")
        
        # Find active patrol
        patrol = PatrolService.get_active_patrol(stream.drone.drone_id)

        session = StreamSession.objects.create(
            stream=stream,
            patrol=patrol,
            kafka_topic=settings.KAFKA_TOPICS['RAW_FRAMES']
        )
        
        producer = get_kafka_producer()
        
        # OPEN CV Capture is deprecated for this stream type
        # In the future, this task might be removed entirely as ESP32 pushes directly to WS
        cap = cv2.VideoCapture() 
        
        if not cap.isOpened():
            logger.error(f"Failed to initialize capture for stream {stream_id}")
            # Non-blocking for now
        
        frame_count = 0
        consecutive_failures = 0
        
        while stream.is_active:
            ret, frame = cap.read()
            
            if not ret:
                consecutive_failures += 1
                logger.warning(f"Failed to read frame from {stream_id}, attempt {consecutive_failures}")
                
                if consecutive_failures >= 10:
                    logger.error(f"Too many consecutive failures, stopping stream {stream_id}")
                    break
                
                continue
            
            consecutive_failures = 0
            frame_count += 1
      
            # Every frame instead of every 3rd for better FPS
            if True: 

                try:
                    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                    frame_base64 = base64.b64encode(buffer).decode('utf-8')
                    
                    try:
                        gps = stream.drone.gps_locations.latest('timestamp')
                        gps_data = {
                            'latitude': float(gps.latitude),
                            'longitude': float(gps.longitude),
                            'altitude': gps.altitude
                        }
                    except Exception:
                        # Fallback if no GPS data
                        gps_data = {
                            'latitude': 0.0,
                            'longitude': 0.0,
                            'altitude': 0.0
                        }

                    
                    # Create message
                    message = {
                        'stream_id': str(stream.stream_id),
                        'drone_id': stream.drone.drone_id,
                        'frame_number': frame_count,
                        'timestamp': timezone.now().isoformat(),
                        'frame_data': frame_base64,
                        'gps': gps_data,
                        'resolution': stream.resolution,
                        'frame_rate': stream.frame_rate
                    }
                    
                    producer.send(settings.KAFKA_TOPICS['RAW_FRAMES'], value=message)
                   
                    session.frames_processed += 1
                    
                    # Save every 30 frames
                    if frame_count % 30 == 0:
                        session.save(update_fields=['frames_processed'])
                    
                except Exception as e:
                    logger.error(f"Error publishing frame to Kafka: {e}", exc_info=True)
            
            if frame_count % 300 == 0:
                logger.info(f"Processed {frame_count} frames from stream {stream_id}")
           
            if frame_count % 100 == 0:
                stream.refresh_from_db()
        
        # Cleanup
        cap.release()
        session.end_time = timezone.now()
        session.save()
        
        duration = (session.end_time - session.start_time).total_seconds()
        fps = session.frames_processed / duration if duration > 0 else 0
        
        logger.info(
            f"Stream processing completed: {stream_id}, "
            f"Frames: {session.frames_processed}, "
            f"Duration: {duration:.2f}s, "
            f"FPS: {fps:.2f}"
        )
        
    except VideoStream.DoesNotExist:
        logger.error(f"Stream {stream_id} not found")
    except cv2.error as e:
        logger.error(f"OpenCV error processing stream {stream_id}: {e}")
        raise self.retry(exc=e, countdown=60)
    except Exception as e:
        logger.error(f"Unexpected error processing stream {stream_id}: {e}", exc_info=True)
        # Ensure we don't leave zombie streams if possible, but the loop checks is_active.
        raise


@shared_task
def cleanup_old_sessions():

    from .models import StreamSession
    
    logger.info("Starting cleanup_old_sessions task")
    
    one_hour_ago = timezone.now() - timedelta(hours=1)
    
    # Find orphaned sessions
    orphaned = StreamSession.objects.filter(
        end_time__isnull=True,
        start_time__lt=one_hour_ago,
        stream__is_active=False
    )
    
    cleaned_count = 0
    
    for session in orphaned:
        session.end_time = timezone.now()
        session.save(update_fields=['end_time'])
        logger.info(f"Cleaned up orphaned session: {session.id}")
        cleaned_count += 1
    
    logger.info(f"Cleanup completed: {cleaned_count} sessions cleaned")
    return cleaned_count


@shared_task
def monitor_stream_health():
    from .models import VideoStream
    
    logger.info("Starting monitor_stream_health task")
    
    active_streams = VideoStream.objects.filter(is_active=True).select_related('drone')
    
    health_report = {
        'total_active_streams': active_streams.count(),
        'healthy_streams': 0,
        'low_fps_streams': [],
        'stalled_streams': [],
        'orphaned_streams': []
    }
    
    for stream in active_streams:
        session = stream.sessions.filter(end_time__isnull=True).first()
        
        if session:
            duration = (timezone.now() - session.start_time).total_seconds()
            fps = session.frames_processed / duration if duration > 0 else 0
 
            if fps < 5:
                if duration > 10:
                    logger.warning(f"Low FPS on stream {stream.stream_id}: {fps:.2f} FPS")
                    health_report['low_fps_streams'].append(str(stream.stream_id))
            
            if fps < 0.5 and duration > 60:
                logger.error(f"Stream {stream.stream_id} appears stalled (FPS: {fps:.2f})")
                health_report['stalled_streams'].append(str(stream.stream_id))
           
                try:
                    from apps.notifications.tasks import send_notification
                    if hasattr(stream.drone, 'assigned_officer') and stream.drone.assigned_officer:
                        send_notification.delay(
                            user_id=stream.drone.assigned_officer.id,
                            title='Stream Stalled',
                            message=f'Stream from {stream.drone.name} has stalled',
                            notification_type='stream_health'
                        )
                except ImportError:
                    logger.warning("Notifications app not found or send_notification task missing")
            
            if fps >= 5:
                health_report['healthy_streams'] += 1
        else:
            logger.error(f"Stream {stream.stream_id} marked active but has no session")
            health_report['orphaned_streams'].append(str(stream.stream_id))
            stream.is_active = False
            stream.save(update_fields=['is_active'])
    
    logger.info(f"Health check completed: {health_report}")
    return health_report
@shared_task(bind=True)
def simulate_stream_task(self, stream_id, patrol_id=None, video_file='computer_vision/traffic_sample.mp4'):
    """
    Simulate a live stream by reading from a video file and publishing to Kafka.
    Can be associated with an active patrol.
    """
    import os
    import time
    from django.conf import settings
    from apps.patrols.models import Patrol
    
    try:
        stream = VideoStream.objects.get(id=stream_id)
        patrol = Patrol.objects.get(id=patrol_id) if patrol_id else None
        
        # Resolve absolute path
        base_dir = settings.BASE_DIR
        abs_video_path = os.path.join(base_dir, video_file)
        
        if not os.path.exists(abs_video_path):
            logger.error(f"Simulation file not found: {abs_video_path}")
            return
            
        stream.is_active = True
        stream.save(update_fields=['is_active'])
        
        session = StreamSession.objects.create(
            stream=stream,
            patrol=patrol,
            kafka_topic=settings.KAFKA_TOPICS['RAW_FRAMES']
        )
        
        producer = get_kafka_producer()
        
        logger.info(f"Starting simulation for stream {stream_id}, patrol {patrol_id}")
        
        frame_count = 0
        while stream.is_active:
            cap = cv2.VideoCapture(abs_video_path)
            if not cap.isOpened():
                logger.error(f"Failed to open simulation video: {abs_video_path}")
                break
                
            fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            delay = 1.0 / fps
            
            while cap.isOpened() and stream.is_active:
                ret, frame = cap.read()
                if not ret:
                    break # Restart loop if finished
                    
                frame_count += 1
                
                # Every frame instead of every 2nd for maximum smoothness
                if True:
                    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                    frame_base64 = base64.b64encode(buffer).decode('utf-8')
                    
                    message = {
                        'stream_id': str(stream.stream_id),
                        'drone_id': stream.drone.drone_id,
                        'frame_number': frame_count,
                        'timestamp': timezone.now().isoformat(),
                        'frame_data': frame_base64,
                        'gps': {'latitude': -17.8252, 'longitude': 31.0335, 'altitude': 50.0},
                        'resolution': '1920x1080',
                        'frame_rate': fps,
                    }
                    
                    producer.send(settings.KAFKA_TOPICS['RAW_FRAMES'], value=message)
                    # producer.flush() # Flushing every frame can be slow, let Kafka buffer
                    session.frames_processed += 1
                    
                    if frame_count % 30 == 0:
                        session.save(update_fields=['frames_processed'])
                
                    # Throttle to match target FPS
                    time.sleep(delay)
                
                # Refresh stream status
                if frame_count % 100 == 0:
                    stream.refresh_from_db()
            
            cap.release()
            
            # If not looping, we'd break here. For now, assume a continuous loop for simulation
            # but check is_active to allow stopping.
            if not stream.is_active:
                break
                
        session.end_time = timezone.now()
        session.save()
        logger.info(f"Simulation completed for stream {stream_id}")
        
    except Exception as e:
        logger.error(f"Error in simulate_stream_task: {e}", exc_info=True)
        if 'stream' in locals():
            stream.is_active = False
            stream.save(update_fields=['is_active'])
