from rest_framework import serializers
from .models import Notification, NotificationPreference
from courses.serializers import CourseSerializer
from authentication.models import User

class NotificationSerializer(serializers.ModelSerializer):
    related_course = CourseSerializer(read_only=True)
    
    class Meta:
        model = Notification
        fields = '__all__'
        read_only_fields = [
            'user', 'created_at', 'updated_at', 
            'notification_type', 'title', 'message'
        ]

class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = '__all__'
        read_only_fields = ['user']

class NotificationMarkAsReadSerializer(serializers.Serializer):
    ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=True
    )
    all = serializers.BooleanField(default=False)

class NotificationCountSerializer(serializers.Serializer):
    unread_count = serializers.IntegerField()