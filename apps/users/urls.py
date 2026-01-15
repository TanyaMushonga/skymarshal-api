from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views.admin_auth import AdminLoginView, AdminPasswordResetRequestView
from .views.officer_auth import (
    OfficerLoginView, OfficerPasswordResetRequestView, OfficerPasswordResetVerifyView
)
from .views.shared_auth import Verify2FAView, PasswordResetConfirmView
from .views.users import UserViewSet

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')

urlpatterns = [
    path('auth/login/admin/', AdminLoginView.as_view(), name='admin_login'),
    path('auth/login/officer/', OfficerLoginView.as_view(), name='officer_login'),
    path('auth/verify-2fa/', Verify2FAView.as_view(), name='verify_2fa'),
    path('auth/password-reset/admin/', AdminPasswordResetRequestView.as_view(), name='admin_password_reset_request'),
    path('auth/password-reset/officer/request/', OfficerPasswordResetRequestView.as_view(), name='officer_password_reset_request'),
    path('auth/password-reset/officer/verify/', OfficerPasswordResetVerifyView.as_view(), name='officer_password_reset_verify'),
    path('auth/password-reset/confirm/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('', include(router.urls)),
]
