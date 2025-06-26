from rest_framework import viewsets, generics, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta
from django_filters.rest_framework import DjangoFilterBackend

from core.views import BaseModelViewSet
from .models import (
    CalendarEvent, CalendarNotification, UserCalendarSettings,
    ContentReleaseSchedule, ContentReleaseRule, StudentProgressOverride
)
from .serializers import (
    CalendarEventSerializer, CalendarNotificationSerializer,
    UserCalendarSettingsSerializer, ContentReleaseScheduleSerializer,
    ContentReleaseRuleSerializer, StudentProgressOverrideSerializer
)
from courses.models import Course
from authentication.models import User

class CalendarEventViewSet(BaseModelViewSet):
    serializer_class = CalendarEventSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['event_type', 'course_event_type', 'status', 'priority', 'course', 'section', 'lecture']

    def get_queryset(self):
        # Admin/superuser gets access to all events
        if self.request.user.is_staff or self.request.user.is_superuser:
            queryset = CalendarEvent.objects.all()
        else:
            # Regular users use permission-based filtering
            queryset = CalendarEvent.objects.filter(
                Q(attendees=self.request.user) | 
                Q(course__instructor=self.request.user) |
                Q(created_by=self.request.user)
            ).distinct()
        
        queryset = queryset.select_related(
            'course', 'section', 'lecture', 'created_by'
        ).prefetch_related('attendees')
        
        # Date range filtering
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date and end_date:
            queryset = queryset.filter(
                start_time__gte=start_date,
                start_time__lte=end_date
            )
        
        # Course-specific filtering
        course_id = self.request.query_params.get('course_id')
        if course_id:
            queryset = queryset.filter(course_id=course_id)
        
        return queryset.order_by('start_time')

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        now = timezone.now()
        thirty_days_later = now + timedelta(days=30)
        
        events = self.get_queryset().filter(
            start_time__gte=now,
            start_time__lte=thirty_days_later,
            status='scheduled'
        )
        
        serializer = self.get_serializer(events, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        original_event = self.get_object()
        new_event = CalendarEvent.objects.create(
            title=f"{original_event.title} (Copy)",
            description=original_event.description,
            event_type=original_event.event_type,
            course_event_type=original_event.course_event_type,
            course=original_event.course,
            section=original_event.section,
            lecture=original_event.lecture,
            start_time=original_event.start_time + timedelta(days=7),
            end_time=original_event.end_time + timedelta(days=7) if original_event.end_time else None,
            is_all_day=original_event.is_all_day,
            status='scheduled',
            priority=original_event.priority,
            location=original_event.location,
            meeting_url=original_event.meeting_url,
            notes=original_event.notes,
            created_by=request.user,
            is_recurring=False,
            color=original_event.color
        )
        new_event.attendees.set(original_event.attendees.all())
        
        serializer = self.get_serializer(new_event)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class CalendarNotificationViewSet(BaseModelViewSet):
    serializer_class = CalendarNotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Admin/superuser gets access to all notifications
        if self.request.user.is_staff or self.request.user.is_superuser:
            queryset = CalendarNotification.objects.all()
        else:
            # Regular users can only see their own notifications
            queryset = CalendarNotification.objects.filter(user=self.request.user)
        
        return queryset.select_related('event', 'user')

class UserCalendarSettingsViewSet(BaseModelViewSet):
    serializer_class = UserCalendarSettingsSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Admin/superuser gets access to all calendar settings
        if self.request.user.is_staff or self.request.user.is_superuser:
            return UserCalendarSettings.objects.all()
        else:
            # Regular users can only see their own settings
            return UserCalendarSettings.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class ContentReleaseScheduleViewSet(BaseModelViewSet):
    serializer_class = ContentReleaseScheduleSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        course_id = self.request.query_params.get('course_id')
        
        # Admin/superuser gets access to all schedules
        if self.request.user.is_staff or self.request.user.is_superuser:
            queryset = ContentReleaseSchedule.objects.all()
        else:
            # Use the same inclusive approach as CalendarEventViewSet for regular users
            queryset = ContentReleaseSchedule.objects.filter(
                Q(course__instructor=self.request.user) |  # User is instructor
                Q(created_by=self.request.user) |          # User created the schedule
                Q(course__enrollments__student=self.request.user)  # User is enrolled in course
            ).distinct()
        
        queryset = queryset.select_related('course').order_by('created_at')
        
        # If course_id is provided, filter by it
        if course_id:
            queryset = queryset.filter(course_id=course_id)
        
        return queryset

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        # Ensure created_by is set when updating as well
        if not serializer.instance.created_by:
            serializer.save(created_by=self.request.user)
        else:
            serializer.save()

    def create(self, request, *args, **kwargs):
        course_id = request.data.get('course_id')
        if not course_id:
            return Response({'error': 'course_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Check if schedule already exists - but use the same filtering logic
            if self.request.user.is_staff or self.request.user.is_superuser:
                # Admin can access any schedule
                schedule = ContentReleaseSchedule.objects.filter(course_id=course_id).first()
            else:
                # Regular users use permission-based filtering
                schedule = ContentReleaseSchedule.objects.filter(
                    Q(course_id=course_id) &
                    (Q(course__instructor=self.request.user) |
                     Q(created_by=self.request.user) |
                     Q(course__enrollments__student=self.request.user))
                ).first()
            
            if schedule:
                serializer = self.get_serializer(schedule, data=request.data, partial=True)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data)
            else:
                return super().create(request, *args, **kwargs)
        except Exception as e:
            return super().create(request, *args, **kwargs)

    @action(detail=True, methods=['post'])
    def generate_events(self, request, pk=None):
        schedule = self.get_object()
        rules = schedule.rules.all()
        
        events_created = 0
        for rule in rules:
            if rule.trigger == 'date' and rule.release_date:
                event, created = CalendarEvent.objects.get_or_create(
                    title=f"Content Release: {rule.section.title if rule.section else rule.lecture.title if rule.lecture else 'Course Content'}",
                    description=f"Automatic content release for {schedule.course.title}",
                    event_type='course',
                    course_event_type='release',
                    course=schedule.course,
                    section=rule.section,
                    lecture=rule.lecture,
                    start_time=rule.release_date,
                    end_time=rule.release_date + timedelta(hours=1),
                    status='scheduled',
                    created_by=request.user
                )
                if created:
                    rule.release_event = event
                    rule.save()
                    events_created += 1
        
        return Response({
            'status': 'success',
            'events_created': events_created,
            'message': f'Generated {events_created} calendar events for release schedule'
        })
    
class ContentReleaseRuleViewSet(BaseModelViewSet):
    serializer_class = ContentReleaseRuleSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        schedule_id = self.request.query_params.get('schedule_id')
        
        if self.request.user.is_staff or self.request.user.is_superuser:
            # Admin can see all rules
            queryset = ContentReleaseRule.objects.all()
        else:
            # Regular users need proper permissions to the schedule
            # Use a more inclusive approach for rule access
            queryset = ContentReleaseRule.objects.filter(
                Q(schedule__course__instructor=self.request.user) |
                Q(schedule__created_by=self.request.user) |
                Q(schedule__course__enrollments__student=self.request.user) |
                Q(created_by=self.request.user)  # Allow access to rules created by user
            ).distinct()
        
        # Apply schedule_id filter if provided
        if schedule_id:
            queryset = queryset.filter(schedule_id=schedule_id)
        
        return queryset.select_related(
            'schedule', 'section', 'lecture', 'quiz', 'release_event'
        )

    def get_object(self):
        """
        Override get_object to provide better error handling and 
        ensure the user has permission to access the specific rule
        """
        obj = super().get_object()
        
        # Double-check permissions for the specific object
        if not (self.request.user.is_staff or self.request.user.is_superuser):
            # Check if user has permission to access this rule
            has_permission = (
                obj.schedule.course.instructor == self.request.user or
                obj.schedule.created_by == self.request.user or
                obj.created_by == self.request.user or
                obj.schedule.course.enrollments.filter(student=self.request.user).exists()
            )
            
            if not has_permission:
                from django.core.exceptions import PermissionDenied
                raise PermissionDenied("You don't have permission to access this rule")
        
        return obj

    def perform_create(self, serializer):
        """Ensure created_by is set when creating a rule"""
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        """Ensure created_by is set when updating a rule if not already set"""
        if not serializer.instance.created_by:
            serializer.save(created_by=self.request.user)
        else:
            serializer.save()

class StudentProgressOverrideViewSet(BaseModelViewSet):
    serializer_class = StudentProgressOverrideSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        rule_id = self.request.query_params.get('rule_id')
        student_id = self.request.query_params.get('student_id')
        
        if self.request.user.is_staff or self.request.user.is_superuser:
            # Admin can see all overrides
            queryset = StudentProgressOverride.objects.all()
        else:
            # Regular users can only see overrides for courses they instruct or rules they created
            queryset = StudentProgressOverride.objects.filter(
                Q(rule__schedule__course__instructor=self.request.user) |
                Q(rule__schedule__created_by=self.request.user)
            )
        
        if rule_id:
            queryset = queryset.filter(rule_id=rule_id)
        if student_id:
            queryset = queryset.filter(student_id=student_id)
        
        return queryset.select_related('student', 'rule')

class CourseEventsView(generics.ListAPIView):
    serializer_class = CalendarEventSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        course_id = self.kwargs['course_id']
        
        if self.request.user.is_staff or self.request.user.is_superuser:
            # Admin can see all events for the course
            queryset = CalendarEvent.objects.filter(course_id=course_id)
        else:
            # Regular users use permission-based filtering
            queryset = CalendarEvent.objects.filter(
                Q(course_id=course_id) &
                (Q(attendees=self.request.user) | 
                 Q(course__instructor=self.request.user) |
                 Q(created_by=self.request.user))
            ).distinct()
        
        return queryset.order_by('start_time')