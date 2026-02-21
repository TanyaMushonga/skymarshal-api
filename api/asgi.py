"""
ASGI config for api project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')

# Import routing after settings are configured
from apps.notifications.routing import websocket_urlpatterns as notifications_urls
from apps.stream_ingestion.routing import websocket_urlpatterns as streams_urls

websocket_urlpatterns = notifications_urls + streams_urls

# No AuthMiddlewareStack - consumer handles authentication via first message
application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": URLRouter(websocket_urlpatterns),
})
