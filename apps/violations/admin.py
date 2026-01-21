from django.contrib import admin
from .models import Violation

@admin.register(Violation)
class ViolationAdmin(admin.ModelAdmin):
    list_display = ('id', 'violation_type', 'status', 'fine_amount', 'get_drone', 'get_timestamp')
    list_filter = ('violation_type', 'status')
    search_fields = ('detection__drone__drone_id', 'detection__license_plate')
    
    def get_drone(self, obj):
        return obj.detection.drone.drone_id
    get_drone.short_description = 'Drone'
    
    def get_timestamp(self, obj):
        return obj.detection.timestamp
    get_timestamp.short_description = 'Timestamp'
