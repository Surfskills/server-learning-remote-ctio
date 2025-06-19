# views.py
from rest_framework import viewsets, generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.decorators import action
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta
from core.views import BaseModelViewSet
from core.permissions import IsInstructor, IsStudent
from .models import (
    CalendarEvent,
    CalendarNotification,
    CalendarPermissions,
    PlannedCourseRelease,
    StudentProgressControl,
    DripSchedule,
    DripScheduleEntry
)
from .serializers import (
    CalendarEventSerializer,
    CalendarNotificationSerializer,
    CalendarPermissionsSerializer,
    PlannedCourseReleaseSerializer,
    StudentProgressControlSerializer,
    DripScheduleSerializer,
    DripScheduleEntrySerializer
)

class CalendarEventViewSet(BaseModelViewSet):
    serializer_class = CalendarEventSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = CalendarEvent.objects.filter(
            Q(attendees=self.request.user) | 
            Q(course__instructor=self.request.user) |
            Q(created_by=self.request.user)
        ).distinct()
        
        course_id = self.request.query_params.get('course_id')
        if course_id:
            queryset = queryset.filter(course_id=course_id)
        
        event_type = self.request.query_params.get('event_type')
        if event_type:
            queryset = queryset.filter(event_type=event_type)
        
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date and end_date:
            queryset = queryset.filter(
                start_time__gte=start_date,
                start_time__lte=end_date
            )
        
        return queryset

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def add_attendee(self, request, pk=None):
        event = self.get_object()
        user_id = request.data.get('user_id')
        if not user_id:
            return Response({'detail': 'user_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(pk=user_id)
            event.attendees.add(user)
            return Response({'detail': 'Attendee added successfully'}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({'detail': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'])
    def remove_attendee(self, request, pk=None):
        event = self.get_object()
        user_id = request.data.get('user_id')
        if not user_id:
            return Response({'detail': 'user_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(pk=user_id)
            event.attendees.remove(user)
            return Response({'detail': 'Attendee removed successfully'}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({'detail': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

class CalendarNotificationViewSet(BaseModelViewSet):
    serializer_class = CalendarNotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return CalendarNotification.objects.filter(user=self.request.user)



class CalendarPermissionsViewSet(BaseModelViewSet):
    serializer_class = CalendarPermissionsSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return CalendarPermissions.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class PlannedCourseReleaseViewSet(BaseModelViewSet):
    serializer_class = PlannedCourseReleaseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return PlannedCourseRelease.objects.filter(student=self.request.user)

class StudentProgressControlViewSet(BaseModelViewSet):
    serializer_class = StudentProgressControlSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return StudentProgressControl.objects.filter(student=self.request.user)

class DripScheduleViewSet(BaseModelViewSet):
    serializer_class = DripScheduleSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        course_id = self.request.query_params.get('course_id')
        if course_id:
            return DripSchedule.objects.filter(course_id=course_id)
        return DripSchedule.objects.all()

class DripScheduleEntryViewSet(BaseModelViewSet):
    serializer_class = DripScheduleEntrySerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        schedule_id = self.request.query_params.get('schedule_id')
        if schedule_id:
            return DripScheduleEntry.objects.filter(schedule_id=schedule_id)
        return DripScheduleEntry.objects.all()

class UpcomingEventsView(generics.ListAPIView):
    serializer_class = CalendarEventSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        now = timezone.now()
        thirty_days_from_now = now + timedelta(days=30)
        return CalendarEvent.objects.filter(
            Q(attendees=self.request.user) | 
            Q(course__instructor=self.request.user) |
            Q(created_by=self.request.user),
            start_time__gte=now,
            start_time__lte=thirty_days_from_now,
            status='scheduled'
        ).order_by('start_time')

class UserEventsView(generics.ListAPIView):
    serializer_class = CalendarEventSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        queryset = CalendarEvent.objects.filter(
            Q(attendees=self.request.user) | 
            Q(course__instructor=self.request.user) |
            Q(created_by=self.request.user)
        ).distinct()
        
        if start_date and end_date:
            queryset = queryset.filter(
                start_time__gte=start_date,
                start_time__lte=end_date
            )
        
        return queryset.order_by('start_time')