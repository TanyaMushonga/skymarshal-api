from django.urls import path
from .views.auth import (
    AdminLoginView, OfficerLoginView, Verify2FAView, 
    AdminPasswordResetRequestView, OfficerPasswordResetRequestView, 
    OfficerPasswordResetVerifyView, PasswordResetConfirmView
)
from .views.users import AdminCreateUserView

urlpatterns = [
    # Auth Endpoints - Login
    path('auth/login/admin/', AdminLoginView.as_view(), name='admin_login'),
    path('auth/login/officer/', OfficerLoginView.as_view(), name='officer_login'),
    
    # 2FA Verification (Used by both after login if 2FA enabled, but mostly likely via login response handling)
    path('auth/verify-2fa/', Verify2FAView.as_view(), name='verify_2fa'),
    
    # Password Reset - Admin (Web/Email)
    path('auth/password-reset/admin/', AdminPasswordResetRequestView.as_view(), name='admin_password_reset_request'),
    
    # Password Reset - Officer (Mobile/SMS)
    path('auth/password-reset/officer/request/', OfficerPasswordResetRequestView.as_view(), name='officer_password_reset_request'),
    path('auth/password-reset/officer/verify/', OfficerPasswordResetVerifyView.as_view(), name='officer_password_reset_verify'),
    
    # Password Reset - Confirm (Shared)
    path('auth/password-reset/confirm/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),

    # User Management
    path('users/create/', AdminCreateUserView.as_view(), name='admin_create_user'),
]
