from rest_framework import status, views, permissions, generics
from rest_framework.response import Response
from django.conf import settings
from django.core.cache import cache
from django.utils.crypto import get_random_string

from ..serializers.auth import AdminLoginSerializer, AdminPasswordResetSerializer
from .shared_auth import BaseLoginView, RESET_TOKEN_EXPIRY
from apps.core.tasks import send_email_task
from ..models import User

class AdminLoginView(BaseLoginView):
    serializer_class = AdminLoginSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        return self.process_login(user)

class AdminPasswordResetRequestView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = AdminPasswordResetSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        
        try:
            user = User.objects.get(email=email)
            token = get_random_string(32)
            cache_key = f"pwd_reset_{token}"
            cache.set(cache_key, user.id, timeout=RESET_TOKEN_EXPIRY)
            
            reset_link = f"{settings.FRONTEND_URL}/reset-password?token={token}"
            
            send_email_task.delay(
                user.email,
                "Password Reset Request",
                f"Click here to reset your password: <a href='{reset_link}'>{reset_link}</a>",
                f"Click here to reset your password: {reset_link}"
            )
        except User.DoesNotExist:
            pass
            
        return Response({"detail": "If an account exists, a reset link has been sent."}, status=status.HTTP_200_OK)
