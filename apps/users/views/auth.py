from rest_framework import status, views, permissions
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.conf import settings
from django.core.cache import cache
from django.utils.crypto import get_random_string

from ..serializers.auth import (
    AdminLoginSerializer, OfficerLoginSerializer, Verify2FASerializer, 
    AdminPasswordResetSerializer, OfficerPasswordResetRequestSerializer,
    OfficerPasswordResetVerifySerializer
)
from apps.core.tasks import send_email_task, send_sms_task
from ..models import User

# Constants
OTP_CACHE_PREFIX = "otp_"
OTP_EXPIRY = 300  # 5 minutes
RESET_TOKEN_EXPIRY = 900 # 15 minutes

class BaseLoginView(views.APIView):
    permission_classes = [permissions.AllowAny]
    
    def process_login(self, user):
        # Generate 2FA Code
        code = get_random_string(length=6, allowed_chars='0123456789')
        cache_key = f"{OTP_CACHE_PREFIX}{user.id}"
        cache.set(cache_key, code, timeout=OTP_EXPIRY)

        if user.phone_number:
            send_sms_task.delay(user.phone_number, f"Your Sky Marshal Login Code: {code}")
            method = "SMS"
        else:
            send_email_task.delay(
                user.email, 
                "Your Sky Marshal Login Code", 
                f"Your login code is: <strong>{code}</strong>", 
                f"Your login code is: {code}"
            )
            method = "Email"

        return Response({
            "detail": f"2FA Code sent via {method}", 
            "email": user.email
        }, status=status.HTTP_200_OK)

class AdminLoginView(BaseLoginView):
    serializer_class = AdminLoginSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        return self.process_login(user)

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

class AdminPasswordResetRequestView(views.APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = AdminPasswordResetSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        
        try:
            user = User.objects.get(email=email)
            # Only allow admins to use this flow? Or generic? Keeping generic for now as per "Admin uses email".
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
