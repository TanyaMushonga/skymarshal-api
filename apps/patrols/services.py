from django.core.cache import cache
from .models import Patrol

class PatrolService:
    @staticmethod
    def get_active_patrol(drone_id):
        """
        Get the currently active patrol for a drone.
        Uses caching to avoid hitting the DB on every frame.
        """
        cache_key = f"active_patrol_{drone_id}"
        patrol_id = cache.get(cache_key)
        
        if patrol_id:
            try:
                return Patrol.objects.get(id=patrol_id)
            except Patrol.DoesNotExist:
                cache.delete(cache_key)
    
        try:
            patrol = Patrol.objects.filter(
                drone__drone_id=drone_id, 
                status='ACTIVE'
            ).latest('start_time')
            
            cache.set(cache_key, patrol.id, timeout=60)
            return patrol
            
        except Patrol.DoesNotExist:
            return None

    @staticmethod
    def clear_cache(drone_id):
        cache.delete(f"active_patrol_{drone_id}")
