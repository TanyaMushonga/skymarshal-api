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

    # Receive message from room group
    async def stream_frame(self, event):
        # Send frame data to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'live_frame',
            'frame_data': event['frame_data'],
            'frame_number': event['frame_number'],
            'timestamp': event['timestamp']
        }))
