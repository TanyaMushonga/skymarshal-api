from django.contrib import admin
from .models import Drone, DroneStatus, GPSLocation

@admin.register(Drone)
class DroneAdmin(admin.ModelAdmin):
    list_display = ('serial_number', 'model_type', 'status', 'current_battery_level', 'updated_at')
    list_filter = ('status', 'model_type')
    search_fields = ('serial_number', 'model_type')

@admin.register(DroneStatus)
class DroneStatusAdmin(admin.ModelAdmin):
    list_display = ('drone', 'battery_level', 'signal_strength', 'status', 'updated_at')
    list_filter = ('status', 'drone')
    search_fields = ('drone__name', 'drone__drone_id')

@admin.register(GPSLocation)
class GPSLocationAdmin(admin.ModelAdmin):
    list_display = ('drone', 'timestamp', 'latitude', 'longitude', 'altitude')
    list_filter = ('drone', 'timestamp')
    date_hierarchy = 'timestamp'
