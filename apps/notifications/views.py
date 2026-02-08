from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter
from .models import Notification
from .serializers import NotificationSerializer

class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing and managing notifications
    """
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    
    # Enable filtering and ordering
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['is_read', 'notification_type']
    ordering_fields = ['created_at', 'is_read']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """
        Return notifications for current user only
        """
        return Notification.objects.filter(recipient=self.request.user)
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
    
        notification = self.get_object()
        
        if not notification.is_read:
            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save()
            
        return Response({'status': 'marked as read'})
    
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        
        qs = self.get_queryset().filter(is_read=False)
        count = qs.count()
        qs.update(is_read=True, read_at=timezone.now())
        
        return Response({'status': 'marked all as read', 'count': count})
    
    @action(detail=False, methods=['post'])
    def bulk_delete(self, request):
        """
        Delete multiple notifications at once.
        Expects: {"ids": ["uuid1", "uuid2", ...]}
        """
        notification_ids = request.data.get('ids', [])
        
        if not notification_ids:
            return Response(
                {'error': 'No notification IDs provided'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Filter to only delete user's own notifications
        deleted_count, _ = self.get_queryset().filter(
            id__in=notification_ids
        ).delete()
        
        return Response({
            'status': 'deleted',
            'count': deleted_count
        })
    
    def destroy(self, request, *args, **kwargs):
        """
        Allow deleting notifications
        """
        # ReadOnlyModelViewSet doesn't include destroy by default
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def perform_destroy(self, instance):
        instance.delete()
