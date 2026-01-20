from django.contrib import admin
from .models import Detection

@admin.register(Detection)
class DetectionAdmin(admin.ModelAdmin):
    list_display = ('id', 'drone', 'vehicle_type', 'confidence', 'timestamp', 'has_plate', 'speed')
    list_filter = ('vehicle_type', 'drone', 'timestamp')
    search_fields = ('drone__drone_id', 'license_plate', 'vehicle_type')
    readonly_fields = ('created_at',)
    
    def has_plate(self, obj):
        return bool(obj.license_plate)
    has_plate.boolean = True
