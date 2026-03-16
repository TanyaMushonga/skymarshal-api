import json
from channels.generic.websocket import AsyncWebsocketConsumer
import logging

logger = logging.getLogger(__name__)

class LiveStreamConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.stream_id = self.scope['url_route']['kwargs']['stream_id']
        self.room_group_name = f'live_stream_{self.stream_id}'
        self.authenticated = False
        self.drone_id = None

        # Join live stream group (viewers and the ESP32 itself)
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()
        logger.info(f"WebSocket connected for stream: {self.stream_id}")

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

        # If authenticated as drone, leave the drone command group
        if self.drone_id:
            drone_group = f"drone_{self.drone_id}"
            await self.channel_layer.group_discard(drone_group, self.channel_name)

        logger.info(f"WebSocket disconnected for stream: {self.stream_id}, code: {close_code}")

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        message_type = data.get('type')

        if message_type == 'authenticate':
            await self._handle_authenticate(data)

        elif message_type == 'frame_ingestion':
            await self._handle_frame(data)

    # -------------------------------------------------------------------------
    # Authentication
    # -------------------------------------------------------------------------
    async def _handle_authenticate(self, data):
        drone_id = data.get('drone_id')
        api_key = data.get('api_key')

        if not drone_id or not api_key:
            await self.send(text_data=json.dumps({
                'type': 'auth_failed',
                'message': 'Missing drone_id or api_key'
            }))
            return

        try:
            from channels.db import database_sync_to_async

            @database_sync_to_async
            def verify_and_setup(d_id, key):
                from apps.drones.models import DroneAPIKey
                from apps.stream_ingestion.models import VideoStream, StreamSession
                from apps.patrols.models import Patrol
                from django.conf import settings

                try:
                    api_key_obj = DroneAPIKey.objects.select_related('drone').get(
                        drone__drone_id=d_id,
                        is_active=True
                    )
                    if not (api_key_obj.check_key(key) and api_key_obj.drone.is_active):
                        return False, None, None, None

                    drone = api_key_obj.drone
                    api_key_obj.record_usage()

                    # Get the associated stream
                    stream = VideoStream.objects.filter(drone=drone).first()
                    if not stream:
                        return False, None, None, None

                    # Find any active patrol for this drone
                    patrol = Patrol.objects.filter(drone=drone, status='ACTIVE').first()

                    # Mark stream as active and create a session
                    stream.is_active = True
                    stream.save(update_fields=['is_active'])

                    session = StreamSession.objects.create(
                        stream=stream,
                        patrol=patrol,
                        kafka_topic=settings.KAFKA_TOPICS['RAW_FRAMES']
                    )

                    return True, drone, stream, session

                except DroneAPIKey.DoesNotExist:
                    return False, None, None, None

            authenticated, drone, stream, session = await verify_and_setup(drone_id, api_key)

            if authenticated:
                self.authenticated = True
                self.drone_id = drone.drone_id
                self.session_id = session.id

                # Join drone command group to receive patrol commands from server
                drone_group = f"drone_{self.drone_id}"
                await self.channel_layer.group_add(drone_group, self.channel_name)

                await self.send(text_data=json.dumps({
                    'type': 'auth_success',
                    'stream_id': self.stream_id,
                    'session_id': str(session.id),
                    'patrol_id': session.patrol_id
                }))
                logger.info(f"Authenticated ESP32-CAM for drone: {drone_id}, session: {session.id}")
            else:
                await self.send(text_data=json.dumps({
                    'type': 'auth_failed',
                    'message': 'Invalid credentials'
                }))
                logger.warning(f"Failed auth for drone: {drone_id}")

        except Exception as e:
            logger.error(f"Error during ESP32 authentication: {e}", exc_info=True)
            await self.send(text_data=json.dumps({
                'type': 'auth_failed',
                'message': 'Internal error'
            }))

    # -------------------------------------------------------------------------
    # Frame Ingestion
    # -------------------------------------------------------------------------
    async def _handle_frame(self, data):
        if not self.authenticated:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Unauthorized. Please authenticate first.'
            }))
            return

        frame_data = data.get('frame_data')
        frame_number = data.get('frame_number', 0)
        timestamp = data.get('timestamp')

        # 1. Broadcast to viewers connected to the stream room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'stream_frame',
                'frame_data': frame_data,
                'frame_number': frame_number,
                'timestamp': timestamp,
                'drone_id': self.drone_id,
            }
        )

        # 2. Publish to Kafka for CV processing
        try:
            from apps.core.kafka_config import get_kafka_producer
            from django.conf import settings

            producer = get_kafka_producer()
            message = {
                'stream_id': self.stream_id,
                'frame_number': frame_number,
                'timestamp': timestamp,
                'frame_data': frame_data,
                'drone_id': self.drone_id,
                'is_esp32': True
            }
            producer.send(settings.KAFKA_TOPICS['RAW_FRAMES'], value=message)
        except Exception as e:
            logger.error(f"Error publishing ESP32 frame to Kafka: {e}")

        # 3. Update session frame count periodically
        if frame_number % 30 == 0 and hasattr(self, 'session_id'):
            try:
                from channels.db import database_sync_to_async
                from apps.stream_ingestion.models import StreamSession
                from django.db.models import F

                @database_sync_to_async
                def increment_frames():
                    StreamSession.objects.filter(id=self.session_id).update(
                        frames_processed=F('frames_processed') + 30
                    )

                await increment_frames()
            except Exception as e:
                logger.error(f"Error updating frame count: {e}")

    # -------------------------------------------------------------------------
    # Group message handlers (called by channel layer)
    # -------------------------------------------------------------------------
    async def stream_frame(self, event):
        """Forward a video frame to WebSocket viewer clients."""
        try:
            await self.send(text_data=json.dumps({
                'type': 'live_frame',
                'frame_data': event['frame_data'],
                'frame_number': event['frame_number'],
                'timestamp': event['timestamp'],
            }))
        except Exception as e:
            logger.debug(f"Failed to forward frame to viewer on stream {self.stream_id}: {e}")

    async def patrol_started(self, event):
        """
        Received when a patrol starts.
        Sent to the drone's command group — the ESP32 receives this and starts streaming.
        """
        logger.info(f"Patrol started command received for drone: {event.get('drone_id')}")
        try:
            await self.send(text_data=json.dumps({
                'type': 'patrol_started',
                'patrol_id': event['patrol_id'],
                'stream_id': event['stream_id'],
                'drone_id': event['drone_id'],
            }))
        except Exception as e:
            logger.debug(f"Failed to send patrol_started to drone: {e}")

    async def patrol_ended(self, event):
        """
        Received when a patrol ends.
        Signals the ESP32 to stop sending frames.
        """
        logger.info(f"Patrol ended command received for drone: {event.get('drone_id')}")
        try:
            await self.send(text_data=json.dumps({
                'type': 'patrol_ended',
                'patrol_id': event['patrol_id'],
                'drone_id': event['drone_id'],
            }))
        except Exception as e:
            logger.debug(f"Failed to send patrol_ended to drone: {e}")
