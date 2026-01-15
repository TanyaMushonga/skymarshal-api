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

class AdminPasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()

class OfficerPasswordResetRequestSerializer(serializers.Serializer):
    force_number = serializers.CharField()

class OfficerPasswordResetVerifySerializer(serializers.Serializer):
    force_number = serializers.CharField()
    code = serializers.CharField(max_length=6)

class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True)

class RequestOTPSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    force_number = serializers.CharField(required=False)

    def validate(self, attrs):
        email = attrs.get('email')
        force_number = attrs.get('force_number')

        if not email and not force_number:
            raise serializers.ValidationError(_("Must provide either 'email' or 'force_number'."))
        
        if email and force_number:
            raise serializers.ValidationError(_("Provide either 'email' or 'force_number', not both."))
            
        return attrs
