from rest_framework import status, views, permissions, generics
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.conf import settings
from django.core.cache import cache
from django.utils.crypto import get_random_string

from ..serializers.auth import Verify2FASerializer, PasswordResetConfirmSerializer, RequestOTPSerializer
from ..serializers.users import UserSerializer
from apps.core.tasks import send_email_task, send_sms_task
from ..models import User

# Constants
OTP_CACHE_PREFIX = "otp_"
OTP_EXPIRY = 300  # 5 minutes
RESET_TOKEN_EXPIRY = 900 # 15 minutes

class BaseLoginView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]
    
    def process_login(self, user):
        # Check if 2FA is enabled
        if not user.is_2fa_enabled:
            # Generate Tokens directly
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)
            
            return Response({
                "access": access_token,
                "refresh": refresh_token,
                "user": UserSerializer(user).data,
                "requires_password_change": user.requires_password_change,
                "detail": "Login successful"
            }, status=status.HTTP_200_OK)

        # Generate 2FA Code
        code = get_random_string(length=6, allowed_chars='0123456789')
        cache_key = f"{OTP_CACHE_PREFIX}{user.id}"
        cache.set(cache_key, code, timeout=OTP_EXPIRY)
        if settings.DEBUG:
            print(f"Generated code: {code}")

        # Send Code (Strictly Email)
        if user.email:
             send_email_task.delay(
                user.email, 
                "Your Sky Marshal Login Code", 
                f"Your login code is: <strong>{code}</strong>", 
                f"Your login code is: {code}"
            )
        
        return Response({
            "detail": "2FA Code sent via Email", 
            "email": user.email,
            "2fa_required": True
        }, status=status.HTTP_200_OK)

class Verify2FAView(generics.GenericAPIView):
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
        
        return Response({
            "access": access_token,
            "refresh": refresh_token,
            "user": UserSerializer(user).data,
            "requires_password_change": user.requires_password_change
        }, status=status.HTTP_200_OK)

class PasswordResetConfirmView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = PasswordResetConfirmSerializer
    
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        token = serializer.validated_data['token']
        new_password = serializer.validated_data['new_password']
            
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

class RequestOTPView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = RequestOTPSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data.get('email')
        force_number = serializer.validated_data.get('force_number')
        
        user = None
        try:
            if email:
                user = User.objects.get(email=email)
            elif force_number:
                user = User.objects.get(force_number=force_number)
        except User.DoesNotExist:
            # We return 200 OK even if user not found to prevent user enumeration
            pass
            
        if user:
            # Generate OTP
            code = get_random_string(length=6, allowed_chars='0123456789')
            cache_key = f"{OTP_CACHE_PREFIX}{user.id}"
            cache.set(cache_key, code, timeout=OTP_EXPIRY)
            
            # Send OTP (Strictly Email)
            if user.email:
                 send_email_task.delay(
                    user.email, 
                    "Your Sky Marshal Login Code", 
                    f"Your login code is: <strong>{code}</strong>", 
                    f"Your login code is: {code}"
                )
            
            if settings.DEBUG:
                print(f"Generated resend code: {code}")

        return Response({"detail": "If an account exists, a code has been sent via Email."}, status=status.HTTP_200_OK)
