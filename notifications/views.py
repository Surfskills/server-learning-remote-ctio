from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from .models import Notification, NotificationPreference
from .serializers import (
    NotificationSerializer,
    NotificationPreferenceSerializer,
    NotificationMarkAsReadSerializer,
    NotificationCountSerializer
)
from core.views import BaseModelViewSet
from core.utils import success_response, error_response
from django.db.models import Q

class NotificationViewSet(BaseModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['notification_type', 'is_read']
    search_fields = ['title', 'message']

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).select_related('related_course')

    @action(detail=False, methods=['post'])
    def mark_as_read(self, request):
        serializer = NotificationMarkAsReadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        if serializer.validated_data.get('all'):
            updated = request.user.notifications.filter(is_read=False).update(is_read=True)
            return success_response(f"Marked {updated} notifications as read")
        
        ids = serializer.validated_data.get('ids', [])
        if ids:
            updated = request.user.notifications.filter(
                id__in=ids, 
                is_read=False
            ).update(is_read=True)
            return success_response(f"Marked {updated} notifications as read")
        
        return error_response("No notifications to mark as read", status_code=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        count = request.user.notifications.filter(is_read=False).count()
        return Response(NotificationCountSerializer({
            'unread_count': count
        }).data)

class NotificationPreferenceViewSet(BaseModelViewSet):
    serializer_class = NotificationPreferenceSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'put', 'patch', 'options']

    def get_queryset(self):
        return NotificationPreference.objects.filter(user=self.request.user)

    def get_object(self):
        return self.request.user.notification_preferences

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)