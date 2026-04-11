from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import action, api_view, permission_classes, authentication_classes
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter
from .models import Notification
from .serializers import NotificationSerializer
from .tasks import send_sms_to_citizen

@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def test_sms(request):
    """
    Unauthenticated endpoint to test SMS sending.
    Expects: {"phone_number": "+263...", "message": "Test message"}
    """
    phone_number = request.data.get('phone_number')
    message = request.data.get('message', "This is a test SMS from SkyMarshal.")
    
    if not phone_number:
        return Response(
            {'error': 'phone_number is required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Trigger the task
    send_sms_to_citizen.delay(phone_number, message)
    
    return Response({
        'status': 'success',
        'message': f'SMS task queued for {phone_number}',
        'note': 'The task uses current SMSService (AWS SNS)'
    })

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
        # check for schema generation which doesn't have an authenticated user
        if getattr(self, "swagger_fake_view", False) or not self.request.user.is_authenticated:
            return Notification.objects.none()
            
        return Notification.objects.filter(recipient=self.request.user)
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
    
        notification = self.get_object()
        
        if not notification.is_read:
            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save()
            
        return Response({'status': 'marked as read'})
    
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """
        Return count of unread notifications for current user
        """
        count = self.get_queryset().filter(is_read=False).count()
        return Response({'unread_count': count})

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
