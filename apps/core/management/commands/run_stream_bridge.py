from django.core.management.base import BaseCommand
from django.conf import settings
from apps.core.kafka_config import get_kafka_consumer
from apps.stream_ingestion.models import VideoStream, StreamSession
from apps.patrols.models import Patrol
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
import logging
import signal
import sys

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Bridges processed Kafka frames to WebSocket groups'

    def handle(self, *args, **options):
        topic = settings.KAFKA_TOPICS.get('PROCESSED_FRAMES', 'processed_frames')
        logger.info(f"Starting Stream Bridge on topic: {topic}")
        
        channel_layer = get_channel_layer()
        consumer = get_kafka_consumer(
            topic=topic,
            group_id='skymarshal_stream_bridge_group_v2' # Reset group to see new messages
        )
        logger.info(f"Connected to Kafka topic: {topic}")

        def signal_handler(sig, frame):
            logger.info('Stopping Stream Bridge...')
            consumer.close()
            sys.exit(0)
            
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # In-memory session cache to avoid redundant lookups and batch saves
        session_cache = {}
        SAVE_EVERY_N_FRAMES = 30

        for message in consumer:
            try:
                data = message.value
                stream_id = data.get('stream_id')
                patrol_id = data.get('patrol_id')
                frame_number = data.get('frame_number')
                
                if not stream_id:
                    continue

                # --- Automatic StreamSession Management (Batched) ---
                if patrol_id:
                    cache_key = f"{stream_id}_{patrol_id}"
                    
                    if cache_key not in session_cache:
                        try:
                            stream = VideoStream.objects.filter(stream_id=stream_id).first()
                            if stream:
                                session, created = StreamSession.objects.get_or_create(
                                    stream=stream,
                                    patrol_id=patrol_id,
                                    end_time__isnull=True,
                                    defaults={'kafka_topic': topic}
                                )
                                session_cache[cache_key] = session
                                if created:
                                    logger.info(f"Created new StreamSession for patrol {patrol_id}")
                        except Exception as db_err:
                            logger.error(f"Failed to initialize StreamSession: {db_err}")

                    if cache_key in session_cache:
                        session = session_cache[cache_key]
                        session.frames_processed += 1
                        
                        # Only save to DB every N frames to maximize performance
                        if session.frames_processed % SAVE_EVERY_N_FRAMES == 0:
                            try:
                                session.save(update_fields=['frames_processed'])
                                # Periodically refresh the session from DB to ensure it hasn't been closed
                                # if it was closed elsewhere, end_time would be set.
                                if session.end_time:
                                    del session_cache[cache_key]
                            except Exception as save_err:
                                logger.error(f"Failed to save batched frames count: {save_err}")
                                # Remove from cache to force re-fetch next time
                                del session_cache[cache_key]

                group_name = f'live_stream_{stream_id}'
                
                # Send frame to the WebSocket group
                async_to_sync(channel_layer.group_send)(
                    group_name,
                    {
                        'type': 'stream_frame',
                        'frame_data': data.get('frame_data'),
                        'frame_number': frame_number,
                        'timestamp': data.get('timestamp'),
                        'patrol_id': patrol_id,
                        'source': data.get('source', 'LIVE')
                    }
                )
                
            except Exception as e:
                logger.error(f"Error bridging frame: {e}", exc_info=True)
