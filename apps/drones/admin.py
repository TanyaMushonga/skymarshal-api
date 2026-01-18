from django.contrib import admin
from .models import Drone, Telemetry

@admin.register(Drone)
class DroneAdmin(admin.ModelAdmin):
    list_display = ('serial_number', 'model_type', 'status', 'current_battery_level', 'updated_at')
    list_filter = ('status', 'model_type')
    search_fields = ('serial_number', 'model_type')

@admin.register(Telemetry)
class TelemetryAdmin(admin.ModelAdmin):
    list_display = ('drone', 'timestamp', 'latitude', 'longitude', 'battery_percentage', 'speed')
    list_filter = ('drone', 'timestamp')
    date_hierarchy = 'timestamp'
