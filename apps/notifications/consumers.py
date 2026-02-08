import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        """
        Accept connection without authentication.
        Client must send auth message as first message.
        """
        self.authenticated = False
        self.user = None
        self.group_name = None
        self.heartbeat_task = None
        await self.accept()
    
    async def disconnect(self, close_code):
        # Cancel heartbeat task
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            
        if self.group_name:
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )
    
    async def receive(self, text_data):
        """
        Handle incoming messages from WebSocket
        """
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'error': 'Invalid JSON format'
            }))
            await self.close()
            return
        
        # First message must be authentication
        if not self.authenticated:
            if data.get('type') == 'authenticate':
                await self.handle_authentication(data.get('token'))
            else:
                await self.send(text_data=json.dumps({
                    'error': 'First message must be authentication'
                }))
                await self.close()
        else:
            # Handle pong response from client (optional)
            if data.get('type') == 'pong':
                # Client responded to ping, connection is alive
                pass
            else:
                # Handle other message types if needed
                await self.send(text_data=json.dumps({
                    'error': 'No actions available via client messages'
                }))
    
    async def handle_authentication(self, token):
        """
        Validate JWT token and authenticate user
        """
        if not token:
            await self.send(text_data=json.dumps({
                'error': 'Token required'
            }))
            await self.close()
            return
        
        # Validate token and get user
        user = await self.get_user_from_token(token)
        
        if user and user.is_authenticated:
            self.user = user
            self.authenticated = True
            self.group_name = f"user_{self.user.id}"
            
            # Add to user's personal group
            await self.channel_layer.group_add(
                self.group_name,
                self.channel_name
            )
            
            # Send success message
            await self.send(text_data=json.dumps({
                'type': 'auth_success',
                'message': 'Authentication successful'
            }))
            
            # Start heartbeat
            self.heartbeat_task = asyncio.create_task(self.heartbeat())
        else:
            await self.send(text_data=json.dumps({
                'error': 'Invalid or expired token'
            }))
            await self.close()
    
    async def heartbeat(self):
        """
        Send periodic ping messages to keep connection alive
        """
        try:
            while True:
                await asyncio.sleep(30)  # Send ping every 30 seconds
                await self.send(text_data=json.dumps({
                    'type': 'ping'
                }))
        except asyncio.CancelledError:
            # Task was cancelled, clean exit
            pass
    
    @database_sync_to_async
    def get_user_from_token(self, token_string):
        """
        Extract and validate user from JWT token
        """
        try:
            from rest_framework_simplejwt.tokens import AccessToken
            from apps.users.models import User
            access_token = AccessToken(token_string)
            user_id = access_token['user_id']
            return User.objects.get(id=user_id)
        except Exception:
            from django.contrib.auth.models import AnonymousUser
            return AnonymousUser()

    async def notification_message(self, event):
        """
        Handler for messages sent to the group
        """
        if not self.authenticated:
            return
            
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
