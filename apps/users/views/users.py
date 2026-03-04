from rest_framework import generics, permissions, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.utils.crypto import get_random_string
from ..serializers.users import AdminCreateUserSerializer, UserSerializer
from ..models import User
from apps.core.tasks import send_email_task
from apps.patrols.models import Patrol

class UserViewSet(viewsets.ModelViewSet):
    """
    CRUD ViewSet for Users.
    Only accessible by Admins.
    """
    queryset = User.objects.all().order_by('-created_at')


    def get_queryset(self):
        """
        Exclude the currently logged-in user from the list.
        """
        user = self.request.user
        
        if getattr(self, "swagger_fake_view", False) or not user.is_authenticated:
            return User.objects.none()
            
        return User.objects.exclude(id=user.id).order_by('-created_at')
    # permission_classes = [permissions.IsAdminUser] # Removed in favor of get_permissions

    def get_permissions(self):
        if self.action == 'create':
            return [permissions.AllowAny()]
        if self.action in ['me', 'toggle_duty', 'change_password']:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAdminUser()]

    def get_serializer_class(self):
        if self.action == 'create':
            return AdminCreateUserSerializer
        return UserSerializer

    @action(detail=False, methods=['get', 'put', 'patch'], permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        """
        Get or update the currently logged-in user's profile.
        """
        user = request.user
        if request.method == 'GET':
            serializer = UserSerializer(user)
            return Response(serializer.data)
        
        # For PUT/PATCH, we want to restrict certain fields
        # we can use a partial update
        serializer = UserSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        
        # Security: Prevent non-admins from changing their own role or force_number
        if not user.is_staff:
            restricted_fields = ['role', 'force_number', 'unit_id', 'is_staff', 'is_superuser']
            for field in restricted_fields:
                if field in serializer.validated_data:
                    serializer.validated_data.pop(field)
        
        serializer.save()
        return Response(serializer.data)

    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated], url_path='toggle-duty')
    def toggle_duty(self, request):
        """
        Toggle the currently logged-in officer's duty status.
        Supports explicit status via 'on_duty' boolean in request data.
        """
        user = request.user
        on_duty_param = request.data.get('on_duty')
        
        old_status = user.is_on_duty
        
        if on_duty_param is not None:
            user.is_on_duty = bool(on_duty_param)
        else:
            user.is_on_duty = not user.is_on_duty
            
        user.save(update_fields=['is_on_duty'])
        
        # If changed from on-duty to off-duty, terminate any active patrols
        terminated_count = 0
        if old_status and not user.is_on_duty:
            # Grace period: Don't terminate patrols started in the last minute (fixes frontend race conditions)
            grace_threshold = timezone.now() - timezone.timedelta(seconds=60)
            
            active_patrols = Patrol.objects.filter(
                officer=user, 
                status='ACTIVE',
                start_time__lte=grace_threshold
            )
            terminated_count = active_patrols.count()
            if terminated_count > 0:
                active_patrols.update(
                    status='COMPLETED',
                    end_time=timezone.now()
                )
# Note: Patrols started < 60s ago remain ACTIVE, but officer is now OFF DUTY.
# This mismatch is safer than killing a just-started patrol.
        
        return Response({
            "is_on_duty": user.is_on_duty,
            "previous_status": old_status,
            "terminated_patrols": terminated_count,
            "detail": f"Officer is now {'on duty' if user.is_on_duty else 'off duty'}. {f'{terminated_count} patrol(s) terminated.' if terminated_count > 0 else ''}"
        })

    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def change_password(self, request):
        """
        Change the currently logged-in user's password.
        """
        from ..serializers.auth import ChangePasswordSerializer
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.requires_password_change = False
        user.save()
        
        return Response({"detail": "Password changed successfully."}, status=status.HTTP_200_OK)

    def perform_create(self, serializer):
        temp_password = get_random_string(12)
        user = serializer.save()
        user.set_password(temp_password)
        user.requires_password_change = True
        user.save()

        send_email_task.delay(
            user.email,
            "Welcome to Sky Marshal - Account Created",
            f"Your account has been created. Temporary Password: <strong>{temp_password}</strong>. Please log in and change it immediately.",
            f"Your account has been created. Temporary Password: {temp_password}. Please log in and change it immediately."
        )
