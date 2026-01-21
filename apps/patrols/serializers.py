from rest_framework import serializers
from .models import Patrol
from apps.drones.models import Drone
from apps.users.models import User

class PatrolSerializer(serializers.ModelSerializer):
    drone_id = serializers.CharField(source='drone.drone_id', read_only=True)
    officer_name = serializers.CharField(source='officer.email', read_only=True)
    
    class Meta:
        model = Patrol
        fields = [
            'id', 'drone', 'drone_id', 'officer', 'officer_name', 
            'start_time', 'end_time', 'patrol_config', 'status', 'created_at'
        ]
        read_only_fields = ['start_time', 'end_time', 'status', 'created_at']
