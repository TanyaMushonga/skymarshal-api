from rest_framework import status, views, permissions
from rest_framework.response import Response
from django.core.cache import cache
from django.utils.crypto import get_random_string

from ..serializers.auth import (
    OfficerLoginSerializer, OfficerPasswordResetRequestSerializer, 
    OfficerPasswordResetVerifySerializer
)
from .shared_auth import BaseLoginView, OTP_EXPIRY, RESET_TOKEN_EXPIRY
from apps.core.tasks import send_sms_task
from ..models import User

class OfficerLoginView(BaseLoginView):
    serializer_class = OfficerLoginSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']

        if user.requires_password_change:
             return Response(
                 {"detail": "Password change required.", "requires_password_change": True},
                 status=status.HTTP_403_FORBIDDEN
             )

        return self.process_login(user)

class OfficerPasswordResetRequestView(views.APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = OfficerPasswordResetRequestSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        force_number = serializer.validated_data['force_number']

        try:
            user = User.objects.get(force_number=force_number)
            if not user.phone_number:
                 return Response({"detail": "No phone number associated with this officer."}, status=status.HTTP_400_BAD_REQUEST)

            code = get_random_string(length=6, allowed_chars='0123456789')
            cache_key = f"reset_otp_{user.id}"
            cache.set(cache_key, code, timeout=OTP_EXPIRY)

            send_sms_task.delay(user.phone_number, f"Sky Marshal Password Reset Code: {code}")

        except User.DoesNotExist:
            pass

        return Response({"detail": "If the officer exists, a verification code has been sent."}, status=status.HTTP_200_OK)

class OfficerPasswordResetVerifyView(views.APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = OfficerPasswordResetVerifySerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        force_number = serializer.validated_data['force_number']
        code = serializer.validated_data['code']

        try:
            user = User.objects.get(force_number=force_number)
        except User.DoesNotExist:
            return Response({"detail": "Invalid credentials"}, status=status.HTTP_400_BAD_REQUEST)

        cache_key = f"reset_otp_{user.id}"
        cached_code = cache.get(cache_key)

        if not cached_code or cached_code != code:
             return Response({"detail": "Invalid or expired code"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Code verified. Generate Reset Token (same mechanism as Admin flow)
        cache.delete(cache_key)
        
        token = get_random_string(32)
        reset_token_key = f"pwd_reset_{token}"
        cache.set(reset_token_key, user.id, timeout=RESET_TOKEN_EXPIRY)

        return Response({
            "detail": "Code verified.",
            "reset_token": token
        }, status=status.HTTP_200_OK)
