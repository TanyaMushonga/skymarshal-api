from django.contrib import admin
from .models import VideoStream, StreamSession

@admin.register(VideoStream)
class VideoStreamAdmin(admin.ModelAdmin):
    list_display = ['stream_id', 'drone', 'is_active', 'frame_rate', 'resolution', 'created_at']
    list_filter = ['is_active', 'frame_rate', 'created_at']
    search_fields = ['stream_id', 'drone__drone_id', 'drone__name', 'rtsp_url']
    readonly_fields = ['stream_id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Stream Information', {
            'fields': ('stream_id', 'drone', 'rtsp_url')
        }),
        ('Configuration', {
            'fields': ('frame_rate', 'resolution', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(StreamSession)
class StreamSessionAdmin(admin.ModelAdmin):
    list_display = ['id', 'stream', 'start_time', 'end_time', 'frames_processed', 'duration']
    list_filter = ['start_time', 'kafka_topic']
    search_fields = ['id', 'stream__stream_id', 'stream__drone__name']
    readonly_fields = ['start_time', 'created_at', 'updated_at', 'duration']
    
    def duration(self, obj):
        if obj.end_time:
            delta = obj.end_time - obj.start_time
            return f"{delta.total_seconds():.0f}s"
        return "Active"
    duration.short_description = 'Duration'