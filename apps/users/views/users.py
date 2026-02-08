from rest_framework import generics, permissions, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.utils.crypto import get_random_string
from ..serializers.users import AdminCreateUserSerializer, UserSerializer
from ..models import User
from apps.core.tasks import send_email_task

class UserViewSet(viewsets.ModelViewSet):
    """
    CRUD ViewSet for Users.
    Only accessible by Admins.
    """
    queryset = User.objects.all().order_by('-created_at')
    parser_classes = (MultiPartParser, FormParser)

    def get_queryset(self):
        """
        Exclude the currently logged-in user from the list.
        """
        user = self.request.user
        return User.objects.exclude(id=user.id).order_by('-created_at')
    # permission_classes = [permissions.IsAdminUser] # Removed in favor of get_permissions

    def get_permissions(self):
        if self.action == 'create':
            return [permissions.AllowAny()]
        if self.action == 'me':
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
