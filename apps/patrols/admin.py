from django.contrib import admin
from .models import Patrol

@admin.register(Patrol)
class PatrolAdmin(admin.ModelAdmin):
    list_display = ('id', 'officer', 'drone', 'status', 'start_time', 'get_config_summary', 'created_at')
    list_filter = ('status', 'start_time', 'created_at')
    search_fields = ('officer__email', 'officer__first_name', 'officer__last_name', 'drone__drone_id')
    readonly_fields = ('start_time', 'created_at', 'updated_at')
    ordering = ('-start_time',)
    
    fieldsets = (
        ('General Information', {
            'fields': ('officer', 'drone', 'status')
        }),
        ('Timing', {
            'fields': ('start_time', 'end_time')
        }),
        ('Configuration', {
            'fields': ('patrol_config',),
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_config_summary(self, obj):
        if not obj.patrol_config:
            return "-"
        return str(obj.patrol_config)[:50] + "..." if len(str(obj.patrol_config)) > 50 else str(obj.patrol_config)
    get_config_summary.short_description = 'Configuration'
