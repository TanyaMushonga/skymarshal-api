from rest_framework import serializers
from django.contrib.auth import authenticate
from django.utils.translation import gettext_lazy as _
from ..models import User

class AdminLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        if email and password:
            # We explicitly check against email for admins
            user = authenticate(request=self.context.get('request'), email=email, password=password)
            if not user:
                 raise serializers.ValidationError(_('Unable to log in with provided credentials.'))
            if user.role != 'admin' and not user.is_superuser:
                 raise serializers.ValidationError(_('Access denied. Admin privileges required.'))
        else:
            raise serializers.ValidationError(_('Must include "email" and "password".'))

        attrs['user'] = user
        return attrs

class OfficerLoginSerializer(serializers.Serializer):
    force_number = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        force_number = attrs.get('force_number')
        password = attrs.get('password')

        if force_number and password:
            # Custom authentication for officer using force_number
            # Since standard authenticate() uses USERNAME_FIELD (email), we need a custom backend or manual check
            # For simplicity, we find the user by force_number then check password
            try:
                user = User.objects.get(force_number=force_number)
            except User.DoesNotExist:
                raise serializers.ValidationError(_('Unable to log in with provided credentials.'))
            
            if not user.check_password(password):
                raise serializers.ValidationError(_('Unable to log in with provided credentials.'))

            if not user.is_active:
                raise serializers.ValidationError(_('User account is disabled.'))
                
            if user.role != 'officer':
                 raise serializers.ValidationError(_('Access denied. Officer privileges required.'))

        else:
            raise serializers.ValidationError(_('Must include "force_number" and "password".'))

        attrs['user'] = user
        return attrs

class Verify2FASerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(max_length=6)

class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()
