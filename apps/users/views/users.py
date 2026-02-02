from rest_framework import generics, permissions, viewsets
from django.utils.crypto import get_random_string
from ..serializers.users import AdminCreateUserSerializer, UserSerializer
from ..models import User
from apps.core.tasks import send_email_task

class UserViewSet(viewsets.ModelViewSet):
    """
    CRUD ViewSet for Users.
    Only accessible by Admins.
    """
    queryset = User.objects.all().order_by('-date_joined')
    # permission_classes = [permissions.IsAdminUser] # Removed in favor of get_permissions

    def get_permissions(self):
        if self.action == 'create':
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]

    def get_serializer_class(self):
        if self.action == 'create':
            return AdminCreateUserSerializer
        return UserSerializer

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
