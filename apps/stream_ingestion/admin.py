from django.contrib import admin
from django.utils.html import format_html
from .models import VideoStream, StreamSession

@admin.register(VideoStream)
class VideoStreamAdmin(admin.ModelAdmin):
    """Admin interface for VideoStream"""
    
    list_display = [
        'stream_id_short', 
        'drone_link', 
        'is_active', 
        'is_streaming',
        'resolution',
        'frame_rate',
        'created_at'
    ]
    list_filter = ['is_active', 'resolution', 'frame_rate', 'created_at']
    search_fields = ['stream_id', 'drone__drone_id', 'drone__name', 'rtsp_url']
    readonly_fields = ['stream_id', 'created_at', 'updated_at', 'session_count']
    
    fieldsets = (
        ('Stream Information', {
            'fields': ('stream_id', 'drone', 'rtsp_url')
        }),
        ('Configuration', {
            'fields': ('resolution', 'frame_rate', 'is_active')
        }),
        ('Statistics', {
            'fields': ('session_count',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def stream_id_short(self, obj):
        """Display shortened stream ID"""
        return str(obj.stream_id)[:8] + '...'
    stream_id_short.short_description = 'Stream ID'
    
    def drone_link(self, obj):
        """Link to drone admin page"""
        from django.urls import reverse
        url = reverse('admin:drones_drone_change', args=[obj.drone.id])
        return format_html('<a href="{}">{}</a>', url, obj.drone.name)
    drone_link.short_description = 'Drone'
    
    def is_streaming(self, obj):
        """Check if currently streaming"""
        return obj.sessions.filter(end_time__isnull=True).exists()
    is_streaming.boolean = True
    is_streaming.short_description = 'Streaming'
    
    def session_count(self, obj):
        """Count total sessions"""
        return obj.sessions.count()
    session_count.short_description = 'Total Sessions'


@admin.register(StreamSession)
class StreamSessionAdmin(admin.ModelAdmin):
    """Admin interface for StreamSession"""
    
    list_display = [
        'id_short',
        'stream_link',
        'drone_name',
        'start_time',
        'end_time',
        'duration_display',
        'frames_processed',
        'fps_display',
        'is_active'
    ]
    list_filter = ['start_time', 'kafka_topic']
    search_fields = ['id', 'stream__stream_id', 'stream__drone__name']
    readonly_fields = [
        'start_time', 
        'created_at', 
        'updated_at', 
        'duration_display',
        'fps_display'
    ]
    
    fieldsets = (
        ('Session Information', {
            'fields': ('stream', 'kafka_topic')
        }),
        ('Timing', {
            'fields': ('start_time', 'end_time', 'duration_display')
        }),
        ('Statistics', {
            'fields': ('frames_processed', 'fps_display')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def id_short(self, obj):
        """Display shortened session ID"""
        return str(obj.id)[:8] + '...'
    id_short.short_description = 'Session ID'
    
    def stream_link(self, obj):
        """Link to stream admin page"""
        from django.urls import reverse
        url = reverse('admin:stream_ingestion_videostream_change', args=[obj.stream.id])
        return format_html('<a href="{}">{}</a>', url, str(obj.stream.stream_id)[:8])
    stream_link.short_description = 'Stream'
    
    def drone_name(self, obj):
        """Display drone name"""
        return obj.stream.drone.name
    drone_name.short_description = 'Drone'
    
    def duration_display(self, obj):
        """Display session duration"""
        from django.utils import timezone
        end_time = obj.end_time or timezone.now()
        delta = end_time - obj.start_time
        seconds = delta.total_seconds()
        
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            return f"{seconds/60:.1f}m"
        else:
            return f"{seconds/3600:.2f}h"
    duration_display.short_description = 'Duration'
    
    def fps_display(self, obj):
        """Display FPS"""
        from django.utils import timezone
        end_time = obj.end_time or timezone.now()
        duration = (end_time - obj.start_time).total_seconds()
        
        if duration > 0:
            fps = obj.frames_processed / duration
            return f"{fps:.2f}"
        return "0.00"
    fps_display.short_description = 'FPS'
    
    def is_active(self, obj):
        """Check if session is active"""
        return obj.end_time is None
    is_active.boolean = True
    is_active.short_description = 'Active'