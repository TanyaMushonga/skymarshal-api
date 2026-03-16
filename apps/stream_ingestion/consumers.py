import json
from channels.generic.websocket import AsyncWebsocketConsumer
import logging

logger = logging.getLogger(__name__)

class LiveStreamConsumer(AsyncWebsocketConsumer):
    async def keen_connect(self):
        self.stream_id = self.scope['url_route']['kwargs']['stream_id']
        self.room_group_name = f'live_stream_{self.stream_id}'

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()
        logger.info(f"Accepted WebSocket connection for stream: {self.stream_id}")

    async def connect(self):
        # Allow unauthorized for now for testing, but in production we should check JWT
        await self.keen_connect()

    async def disconnect(self, close_code):
        # Leave room group
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
            logger.info(f"WebSocket disconnected for stream: {self.stream_id}")

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type')

        if message_type == 'authenticate':
            drone_id = data.get('drone_id')
            api_key = data.get('api_key')
            
            if not drone_id or not api_key:
                await self.send(text_data=json.dumps({
                    'type': 'auth_failed',
                    'message': 'Missing drone_id or api_key'
                }))
                return

            # Verify API key
            try:
                from apps.drones.models import DroneAPIKey
                from channels.db import database_sync_to_async
                
                @database_sync_to_async
                def verify_key(d_id, key):
                    try:
                        api_key_obj = DroneAPIKey.objects.select_related('drone').get(
                            drone__drone_id=d_id,
                            is_active=True
                        )
                        if api_key_obj.check_key(key) and api_key_obj.drone.is_active:
                            api_key_obj.record_usage()
                            return True, api_key_obj.drone
                    except DroneAPIKey.DoesNotExist:
                        pass
                    return False, None

                authenticated, drone = await verify_key(drone_id, api_key)
                
                if authenticated:
                    self.authenticated = True
                    self.drone_id = drone_id
                    await self.send(text_data=json.dumps({
                        'type': 'auth_success',
                        'stream_id': self.stream_id
                    }))
                    logger.info(f"Authenticated ESP32-CAM for drone: {drone_id}")
                else:
                    await self.send(text_data=json.dumps({
                        'type': 'auth_failed',
                        'message': 'Invalid credentials'
                    }))
                    logger.warning(f"Failed authentication attempt for drone: {drone_id}")
                    
            except Exception as e:
                logger.error(f"Error during ESP32 authentication: {e}")
                await self.send(text_data=json.dumps({
                    'type': 'auth_failed',
                    'message': 'Internal error'
                }))

        elif message_type == 'frame_ingestion':
            # Only allow if authenticated
            if not getattr(self, 'authenticated', False):
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Unauthorized. Please authenticate first.'
                }))
                return

            # This is where the ESP32-CAM sends frames
            frame_data = data.get('frame_data')
            frame_number = data.get('frame_number', 0)
            timestamp = data.get('timestamp')

            # 1. Broadcast to the room group for real-time viewing
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'stream_frame',
                    'frame_data': frame_data,
                    'frame_number': frame_number,
                    'timestamp': timestamp
                }
            )

            # 2. Publish to Kafka for processing (AI detection, storage, etc.)
            try:
                from apps.core.kafka_config import get_kafka_producer
                from django.conf import settings
                
                producer = get_kafka_producer()
                message = {
                    'stream_id': self.stream_id,
                    'frame_number': frame_number,
                    'timestamp': timestamp,
                    'frame_data': frame_data,
                    'is_esp32': True
                }
                producer.send(settings.KAFKA_TOPICS['RAW_FRAMES'], value=message)
            except Exception as e:
                logger.error(f"Error publishing ESP32 frame to Kafka: {e}")

    # Receive message from room group
    async def stream_frame(self, event):
        # Send frame data to WebSocket
        try:
            await self.send(text_data=json.dumps({
                'type': 'live_frame',
                'frame_data': event['frame_data'],
                'frame_number': event['frame_number'],
                'timestamp': event['timestamp']
            }))
        except Exception as e:
            logger.debug(f"Failed to send frame to {self.stream_id}: {e}")
            # If we fail to send, we might want to discard the group member, 
            # but Channels usually handles this when the connection's state is updated.
