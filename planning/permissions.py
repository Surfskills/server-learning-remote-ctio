# permissions.py
from rest_framework.permissions import BasePermission
from core.permissions import IsAdminUser, IsInstructor, IsStudent

class CanCreateCalendarEvent(BasePermission):
    def has_permission(self, request, view):
        if request.user.is_staff:
            return True
        if hasattr(request.user, 'calendar_permissions'):
            return request.user.calendar_permissions.can_create_events
        return False

class CanEditCalendarEvent(BasePermission):
    def has_permission(self, request, view):
        if request.user.is_staff:
            return True
        if hasattr(request.user, 'calendar_permissions'):
            return request.user.calendar_permissions.can_edit_events
        return False

    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        return obj.created_by == request.user

class CanDeleteCalendarEvent(BasePermission):
    def has_permission(self, request, view):
        if request.user.is_staff:
            return True
        if hasattr(request.user, 'calendar_permissions'):
            return request.user.calendar_permissions.can_delete_events
        return False

    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        return obj.created_by == request.user