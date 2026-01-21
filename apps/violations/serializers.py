from rest_framework import serializers
from .models import Violation

class ViolationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Violation
        fields = '__all__'
