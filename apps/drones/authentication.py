from rest_framework import authentication, exceptions
from .models import DroneAPIKey
import logging
from .tasks import record_api_key_usage

logger = logging.getLogger(__name__)

class DroneAPIKeyAuthentication(authentication.BaseAuthentication):
    """
    Custom authentication for ESP32-CAM drones using API keys
    
    Expected HTTP headers:
    - X-Drone-ID: The drone's unique identifier (e.g., "DRONE_001")
    - X-API-Key: The drone's secret API key (e.g., "sk_drone_abc123...")
    
    Authentication flow:
    1. Extract X-Drone-ID and X-API-Key from request.META
    2. If either header is missing, return None (skip this auth method)
    3. Query DroneAPIKey model with:
       - drone__drone_id = extracted drone_id
       - key = extracted api_key
       - is_active = True
    4. If not found, raise AuthenticationFailed('Invalid drone credentials')
    5. Check if drone.is_active, if not raise AuthenticationFailed('Drone is inactive')
    6. Trigger async task to record_api_key_usage(api_key_obj.id)
    7. Return tuple: (None, api_key_obj.drone)
       - First element: user object (None for drones)
       - Second element: auth object (the Drone instance)
    
    This makes request.auth contain the authenticated Drone object
    """
    
    def authenticate(self, request):
        drone_id = request.META.get('HTTP_X_DRONE_ID')
        api_key = request.META.get('HTTP_X_API_KEY')
        
        if not drone_id or not api_key:
            return None
            
        try:
            api_key_obj = DroneAPIKey.objects.select_related('drone').get(
                drone__drone_id=drone_id,
                key=api_key,
                is_active=True
            )
        except DroneAPIKey.DoesNotExist:
            logger.warning(f"Invalid API key attempt for drone_id: {drone_id}")
            raise exceptions.AuthenticationFailed('Invalid drone credentials')
            
        if not api_key_obj.drone.is_active:
            raise exceptions.AuthenticationFailed('Drone is inactive')
            
        # Record usage asynchronously
        record_api_key_usage.delay(api_key_obj.id)
        
        return (None, api_key_obj.drone)
    
    def authenticate_header(self, request):
        """Return authentication method string for 401 responses"""
        return 'X-Drone-ID, X-API-Key'
