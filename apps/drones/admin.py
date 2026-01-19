from django.contrib import admin
from .models import Drone, DroneStatus, GPSLocation, DroneAPIKey

# Create inline for API key
class DroneAPIKeyInline(admin.StackedInline):
    model = DroneAPIKey
    readonly_fields = ['key', 'created_at', 'last_used', 'usage_count']
    can_delete = False
    extra = 0
    fieldsets = (
        ('API Key Information', {
            'fields': ('key', 'is_active'),
            'description': 'API key for drone authentication. Store this securely!'
        }),
        ('Usage Statistics', {
            'fields': ('last_used', 'usage_count', 'created_at'),
            'classes': ('collapse',)
        }),
    )

# Update existing DroneAdmin to include inline
@admin.register(Drone)
class DroneAdmin(admin.ModelAdmin):
    list_display = ['drone_id', 'name', 'is_active', 'assigned_officer', 'has_api_key', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['drone_id', 'name', 'serial_number']
    inlines = [DroneAPIKeyInline]  # Add this line
    
    def has_api_key(self, obj):
        """Display checkmark if drone has API key"""
        return hasattr(obj, 'api_key')
    has_api_key.boolean = True
    has_api_key.short_description = 'Has API Key'

# Create admin for DroneAPIKey (separate view)
@admin.register(DroneAPIKey)
class DroneAPIKeyAdmin(admin.ModelAdmin):
    list_display = ['drone', 'key_preview', 'is_active', 'last_used', 'usage_count', 'created_at']
    list_filter = ['is_active', 'created_at', 'last_used']
    search_fields = ['drone__drone_id', 'drone__name', 'key']
    readonly_fields = ['hashed_key', 'created_at', 'updated_at', 'last_used', 'usage_count']
    
    fieldsets = (
        ('Drone Association', {
            'fields': ('drone',)
        }),
        ('API Key', {
            'fields': ('hashed_key', 'is_active', 'expires_at'),
            'description': 'WARNING: Key is hashed and cannot be viewed. Regenerate if lost.'
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
    
    def key_preview(self, obj):
        return "********"
    key_preview.short_description = 'API Key'
    
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
