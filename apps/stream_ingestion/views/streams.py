from rest_framework import viewsets, status, filters
from apps.core.pagination import StandardResultsSetPagination
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from apps.core.permissions import IsDroneAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from ..models import VideoStream
from ..serializers import (
    VideoStreamSerializer, 
    StreamRegistrationSerializer,
    StreamSessionSerializer
)
from ..tasks import process_rtsp_stream

class VideoStreamViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing video streams
    """
    
    queryset = VideoStream.objects.select_related('drone').all()
    serializer_class = VideoStreamSerializer
    permission_classes = [IsAuthenticated | IsDroneAuthenticated]
    ordering = ['-created_at']
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active', 'drone__drone_id', 'drone']
    search_fields = ['rtsp_url', 'drone__name', 'drone__drone_id']
    ordering_fields = ['created_at', 'updated_at']
    
    def get_serializer_class(self):
        """Use StreamRegistrationSerializer for create action"""
        if self.action == 'create':
            return StreamRegistrationSerializer
        return VideoStreamSerializer
    
    def create(self, request, *args, **kwargs):
        """
        Create new video stream
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        stream = serializer.save()
        
        # Return full stream data
        output_serializer = VideoStreamSerializer(stream)
        return Response(
            output_serializer.data,
            status=status.HTTP_201_CREATED
        )
    
    def destroy(self, request, *args, **kwargs):
        """
        Delete stream if not active
        """
        instance = self.get_object()
        
        if instance.is_active:
            return Response(
                {'error': 'Cannot delete active stream. Stop the stream first.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """
        Start video stream processing
        POST /api/v1/streams/{id}/start/
        """
        stream = self.get_object()
        
        if stream.is_active:
            return Response(
                {'error': 'Stream is already active'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Set active
        stream.is_active = True
        stream.save(update_fields=['is_active'])
        
        # Start processing task
        task = process_rtsp_stream.delay(str(stream.stream_id))
        
        # Get or create active session
        session = stream.sessions.filter(end_time__isnull=True).first()
        
        return Response({
            'status': 'started',
            'session_id': str(session.id) if session else None,
            'task_id': task.id,
            'message': 'Stream processing started',
            'stream_id': str(stream.stream_id)
        }, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def stop(self, request, pk=None):
        """
        Stop video stream processing
        POST /api/v1/streams/{id}/stop/
        """
        from django.utils import timezone
        
        stream = self.get_object()
        
        if not stream.is_active:
            return Response(
                {'error': 'Stream is not active'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Stop stream
        stream.is_active = False
        stream.save(update_fields=['is_active'])
        
        # End current session
        session = stream.sessions.filter(end_time__isnull=True).first()
        
        if session:
            session.end_time = timezone.now()
            session.save(update_fields=['end_time'])
            
            # Calculate stats
            duration = (session.end_time - session.start_time).total_seconds()
            fps = session.frames_processed / duration if duration > 0 else 0
            
            session_stats = {
                'session_id': str(session.id),
                'frames_processed': session.frames_processed,
                'duration': duration,
                'fps': round(fps, 2)
            }
        else:
            session_stats = None
        
        return Response({
            'status': 'stopped',
            'message': 'Stream stopped successfully',
            'session_stats': session_stats
        }, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """
        Get stream statistics
        GET /api/v1/streams/{id}/stats/
        """
        from django.db.models import Sum
        
        stream = self.get_object()
        sessions = stream.sessions.all()
        completed_sessions = sessions.exclude(end_time__isnull=True)
        
        # Calculate total uptime
        total_uptime = 0
        for session in completed_sessions:
            if session.end_time:
                duration = (session.end_time - session.start_time).total_seconds()
                total_uptime += duration
        
        # Calculate average FPS
        total_frames = sessions.aggregate(Sum('frames_processed'))['frames_processed__sum'] or 0
        avg_fps = total_frames / total_uptime if total_uptime > 0 else 0
        
        # Current session
        current_session = sessions.filter(end_time__isnull=True).first()
        last_completed = completed_sessions.order_by('-end_time').first()
        
        return Response({
            'stream_id': str(stream.stream_id),
            'drone_name': stream.drone.name,
            'drone_id': stream.drone.drone_id,
            'total_sessions': sessions.count(),
            'total_frames': total_frames,
            'total_uptime_seconds': round(total_uptime, 2),
            'average_fps': round(avg_fps, 2),
            'is_currently_active': stream.is_active,
            'current_session': StreamSessionSerializer(current_session).data if current_session else None,
            'last_completed_session': StreamSessionSerializer(last_completed).data if last_completed else None
        }, status=status.HTTP_200_OK)
