import json
from channels.generic.websocket import AsyncWebsocketConsumer

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        
        if not self.user.is_authenticated:
            await self.close()
            return
            
        # Create a group for this user
        self.group_name = f"user_{self.user.id}"
        
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

    async def notification_message(self, event):
        """
        Handler for messages sent to the group
        """
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'id': str(event['id']),
            'title': event['title'],
            'message': event['message'],
            'notification_type': event['notification_type'],
            'created_at': event['created_at'],
            'related_object_id': event.get('related_object_id')
        }))
