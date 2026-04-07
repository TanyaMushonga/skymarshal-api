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
            group_id='skymarshal_stream_bridge_group'
        )

        def signal_handler(sig, frame):
            logger.info('Stopping Stream Bridge...')
            consumer.close()
            sys.exit(0)
            
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        for message in consumer:
            try:
                data = message.value
                stream_id = data.get('stream_id')
                patrol_id = data.get('patrol_id')
                frame_number = data.get('frame_number')
                
                if not stream_id:
                    logger.warning(f"Received frame {frame_number} without stream_id")
                    continue

                # --- Automatic StreamSession Management ---
                if patrol_id:
                    try:
                        # Ensure VideoStream exists
                        stream = VideoStream.objects.filter(stream_id=stream_id).first()
                        if stream:
                            # Use update_or_create logic for the session
                            session, created = StreamSession.objects.get_or_create(
                                stream=stream,
                                patrol_id=patrol_id,
                                end_time__isnull=True,
                                defaults={'kafka_topic': topic}
                            )
                            
                            # Increment frame count
                            session.frames_processed += 1
                            session.save(update_fields=['frames_processed'])
                            
                            if created:
                                logger.info(f"Created new StreamSession for patrol {patrol_id}")
                    except Exception as db_err:
                        logger.error(f"Failed to manage StreamSession: {db_err}")

                group_name = f'live_stream_{stream_id}'
                logger.info(f"Bridging frame {frame_number} for stream {stream_id} to group {group_name}")
                
                # Send frame to the WebSocket group
                async_to_sync(channel_layer.group_send)(
                    group_name,
                    {
                        'type': 'stream_frame',
                        'frame_data': data.get('frame_data'),
                        'frame_number': frame_number,
                        'timestamp': data.get('timestamp'),
                        'patrol_id': patrol_id
                    }
                )
                logger.info(f"Successfully sent frame {frame_number} to group {group_name}")
                
            except Exception as e:
                logger.error(f"Error bridging frame: {e}", exc_info=True)
