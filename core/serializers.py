from rest_framework import serializers
from .models import HealthCheck

class HealthCheckSerializer(serializers.ModelSerializer):
    class Meta:
        model = HealthCheck
        fields = '__all__'
        read_only_fields = ['last_checked']

class EmptySerializer(serializers.Serializer):
    """
    Empty serializer for actions that don't need input
    """
    pass