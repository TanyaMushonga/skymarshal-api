from rest_framework import authentication, exceptions
from ..drones.models import DroneAPIKey
import logging
from ..drones.tasks import record_api_key_usage

logger = logging.getLogger(__name__)

class DroneAPIKeyAuthentication(authentication.BaseAuthentication):
    
    def authenticate(self, request):
        drone_id = request.META.get('HTTP_X_DRONE_ID')
        api_key = request.META.get('HTTP_X_API_KEY')
        
        if not drone_id or not api_key:
            return None
            
        try:
            api_key_obj = DroneAPIKey.objects.select_related('drone').get(
                drone__drone_id=drone_id,
                is_active=True
            )
        except DroneAPIKey.DoesNotExist:
            logger.warning(f"No active API key found for drone_id: {drone_id}")
            raise exceptions.AuthenticationFailed('Invalid drone credentials')

        if not api_key_obj.check_key(api_key):
            logger.warning(f"Invalid API key provided for drone_id: {drone_id}")
            raise exceptions.AuthenticationFailed('Invalid drone credentials')
            
        if not api_key_obj.drone.is_active:
            raise exceptions.AuthenticationFailed('Drone is inactive')
            
        record_api_key_usage.delay(api_key_obj.id)
        
        # Return (drone, auth) - drone now has is_authenticated=True
        return (api_key_obj.drone, api_key_obj)
    
    def authenticate_header(self, request):
        return 'X-Drone-ID, X-API-Key'
