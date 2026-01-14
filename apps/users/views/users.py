from rest_framework import generics, permissions
from django.utils.crypto import get_random_string
from ..serializers.users import AdminCreateUserSerializer
from ..models import User
from apps.core.tasks import send_email_task

class AdminCreateUserView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = AdminCreateUserSerializer
    permission_classes = [permissions.IsAdminUser]

    def perform_create(self, serializer):
        # Generate random temp password
        temp_password = get_random_string(12)
        user = serializer.save()
        user.set_password(temp_password)
        user.requires_password_change = True
        # Role is handled by serializer or model default
        user.save()

        # Send Welcome Email
        send_email_task.delay(
            user.email,
            "Welcome to Sky Marshal - Account Created",
            f"Your account has been created. Temporary Password: <strong>{temp_password}</strong>. Please log in and change it immediately.",
            f"Your account has been created. Temporary Password: {temp_password}. Please log in and change it immediately."
        )
