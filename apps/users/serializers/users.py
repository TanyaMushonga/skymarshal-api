from rest_framework import serializers
from ..models import User

class UserSerializer(serializers.ModelSerializer):
    is_officer = serializers.ReadOnlyField() 
    
    class Meta:
        model = User
        fields = (
            'id', 'email', 'first_name', 'last_name', 'role', 
            'force_number', 'unit_id',
            'is_officer', 'is_certified_pilot', 'pilot_license_number', 'license_expiry_date',
            'phone_number', 'is_2fa_enabled', 'requires_password_change',
            'is_on_duty', 'last_known_lat', 'last_known_lon'
        )
        read_only_fields = ('id', 'is_officer', 'requires_password_change', 'is_2fa_enabled', 'last_known_lat', 'last_known_lon')

class AdminCreateUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'role', 'force_number', 'unit_id', 'phone_number', 'is_certified_pilot', 'pilot_license_number')
    
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value
