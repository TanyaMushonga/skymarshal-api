from rest_framework import status, views, permissions
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.conf import settings
from django.core.cache import cache
from django.utils.crypto import get_random_string

from ..serializers.auth import Verify2FASerializer
from apps.core.tasks import send_email_task, send_sms_task
from ..models import User

# Constants
OTP_CACHE_PREFIX = "otp_"
OTP_EXPIRY = 300  # 5 minutes
RESET_TOKEN_EXPIRY = 900 # 15 minutes

class BaseLoginView(views.APIView):
    permission_classes = [permissions.AllowAny]
    
    def process_login(self, user):
        # Check if 2FA is enabled
        if not user.is_2fa_enabled:
            # Generate Tokens directly
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)
            
            response = Response({
                "access": access_token,
                "refresh": refresh_token,
                "requires_password_change": user.requires_password_change,
                "detail": "Login successful"
            }, status=status.HTTP_200_OK)
            
            response.set_cookie(
                settings.SIMPLE_JWT.get('AUTH_COOKIE', 'access_token'),
                access_token,
                max_age=settings.SIMPLE_JWT.get('ACCESS_TOKEN_LIFETIME').total_seconds(),
                httponly=True,
                samesite='Lax',
                secure=not settings.DEBUG
            )
            return response

        # Generate 2FA Code
        code = get_random_string(length=6, allowed_chars='0123456789')
        cache_key = f"{OTP_CACHE_PREFIX}{user.id}"
        cache.set(cache_key, code, timeout=OTP_EXPIRY)

        # Send Code (Prefer SMS if available, else Email)
        if user.phone_number:
            send_sms_task.delay(user.phone_number, f"Your Sky Marshal Login Code: {code}")
            method = "SMS"
        else:
            # Fallback to email or if specifically requested
            send_email_task.delay(
                user.email, 
                "Your Sky Marshal Login Code", 
                f"Your login code is: <strong>{code}</strong>", 
                f"Your login code is: {code}"
            )
            method = "Email"

        return Response({
            "detail": f"2FA Code sent via {method}", 
            "email": user.email,
            "2fa_required": True
        }, status=status.HTTP_200_OK)

class Verify2FAView(views.APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = Verify2FASerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        code = serializer.validated_data['code']
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"detail": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
            
        cache_key = f"{OTP_CACHE_PREFIX}{user.id}"
        cached_code = cache.get(cache_key)
        
        if not cached_code or cached_code != code:
             return Response({"detail": "Invalid or expired code"}, status=status.HTTP_400_BAD_REQUEST)
             
        cache.delete(cache_key)
        
        # Generate Tokens
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)
        
        response = Response({
            "access": access_token,
            "refresh": refresh_token,
            "requires_password_change": user.requires_password_change
        })
        
        response.set_cookie(
            settings.SIMPLE_JWT.get('AUTH_COOKIE', 'access_token'),
            access_token,
            max_age=settings.SIMPLE_JWT.get('ACCESS_TOKEN_LIFETIME').total_seconds(),
            httponly=True,
            samesite='Lax',
            secure=not settings.DEBUG
        )
        return response

class PasswordResetConfirmView(views.APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        token = request.data.get('token')
        new_password = request.data.get('new_password')
        
        if not token or not new_password:
            return Response({"detail": "Token and new password required"}, status=status.HTTP_400_BAD_REQUEST)
            
        cache_key = f"pwd_reset_{token}"
        user_id = cache.get(cache_key)
        
        if not user_id:
             return Response({"detail": "Invalid or expired token"}, status=status.HTTP_400_BAD_REQUEST)
             
        try:
            user = User.objects.get(id=user_id)
            user.set_password(new_password)
            user.requires_password_change = False
            user.save()
            cache.delete(cache_key)
            return Response({"detail": "Password reset successful"}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
             return Response({"detail": "User not found"}, status=status.HTTP_404_NOT_FOUND)
