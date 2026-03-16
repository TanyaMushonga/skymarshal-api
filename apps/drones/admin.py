from django.contrib import admin
from .models import Drone, DroneStatus, GPSLocation, DroneAPIKey

# Create inline for API key
class DroneAPIKeyInline(admin.StackedInline):
    model = DroneAPIKey
    readonly_fields = ['prefix', 'hashed_key', 'created_at', 'last_used', 'usage_count']
    can_delete = False
    extra = 0
    fieldsets = (
        ('API Key Information', {
            'fields': ('prefix', 'hashed_key', 'is_active'),
            'description': 'API key for drone authentication. Keys are stored as hashes.'
        }),
        ('Usage Statistics', {
            'fields': ('last_used', 'usage_count', 'created_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(Drone)
class DroneAdmin(admin.ModelAdmin):
    list_display = ('drone_id', 'name', 'model', 'is_active', 'assigned_officer', 'is_patrolling_display')
    list_filter = ('model', 'is_active')
    search_fields = ('drone_id', 'name', 'serial_number')
    inlines = [DroneAPIKeyInline]
    
    def is_patrolling_display(self, obj):
        return obj.is_patrolling
    is_patrolling_display.boolean = True
    is_patrolling_display.short_description = 'Patrolling'

# Create admin for DroneAPIKey (separate view)
@admin.register(DroneAPIKey)
class DroneAPIKeyAdmin(admin.ModelAdmin):
    list_display = ['drone', 'prefix', 'is_active', 'last_used', 'usage_count', 'created_at']
    list_filter = ['is_active', 'created_at', 'last_used']
    search_fields = ['drone__drone_id', 'drone__name', 'prefix']
    readonly_fields = ['prefix', 'hashed_key', 'created_at', 'updated_at', 'last_used', 'usage_count']
    
    fieldsets = (
        ('Drone Association', {
            'fields': ('drone',)
        }),
        ('API Key Details', {
            'fields': ('prefix', 'hashed_key', 'is_active'),
            'description': 'WARNING: Key is hashed and cannot be viewed. Regenerate via CLI if lost.'
        }),
        ('Usage Statistics', {
            'fields': ('last_used', 'usage_count'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        """Disable manual creation through admin (use signal instead)"""
        return False

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
