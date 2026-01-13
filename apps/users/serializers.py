from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User
from django.utils.translation import gettext_lazy as _

class UserSerializer(serializers.ModelSerializer):
    is_officer = serializers.ReadOnlyField() # Expose property
    
    class Meta:
        model = User
        fields = (
            'id', 'email', 'first_name', 'last_name', 'role', 
            'badge_number', 'unit_id',
            'is_officer', 'is_certified_pilot', 'pilot_license_number', 'license_expiry_date',
            'phone_number', 'is_2fa_enabled', 'requires_password_change',
            'is_on_duty', 'last_known_lat', 'last_known_lon'
        )
        read_only_fields = ('id', 'is_officer', 'requires_password_change', 'is_2fa_enabled', 'last_known_lat', 'last_known_lon')

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        if email and password:
            user = authenticate(request=self.context.get('request'), email=email, password=password)
            if not user:
                raise serializers.ValidationError(_('Unable to log in with provided credentials.'))
        else:
            raise serializers.ValidationError(_('Must include "email" and "password".'))

        attrs['user'] = user
        return attrs

class Verify2FASerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(max_length=6)

class AdminCreateUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'role', 'badge_number', 'unit_id', 'phone_number', 'is_certified_pilot', 'pilot_license_number')
    
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()
