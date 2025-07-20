from rest_framework import viewsets, generics
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.utils import timezone
from rest_framework.views import APIView
from django.db.models import Avg
from authentication.models import User
from courses.models import Course
from courses.serializers import CourseSerializer
from enrollments.models import Enrollment
from enrollments.serializers import CourseProgressSerializer, EnrollmentSerializer
from payments.models import Order
from planning.models import CalendarEvent
from .models import HealthCheck
from .serializers import HealthCheckSerializer
from .utils import success_response, error_response
from rest_framework import viewsets, generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.decorators import action

# Add these to your existing views.py
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.decorators import action
from django.utils import timezone
from datetime import timedelta
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q
from .models import *
from .serializers import *
from .permissions import *

class HealthCheckView(generics.GenericAPIView):
    """
    Basic health check endpoint
    """
    permission_classes = [AllowAny]

    def get(self, request):
        data = {
            'status': 'healthy',
            'timestamp': timezone.now().isoformat(),
            'service': 'EduPlatform API',
            'version': '1.0.0'
        }
        return success_response(data=data)

class ExtendedHealthCheckView(generics.GenericAPIView):
    """
    Extended health check with system status
    """
    permission_classes = [IsAuthenticated]
    serializer_class = HealthCheckSerializer
    queryset = HealthCheck.objects.all()

    def get(self, request):
        services = self.get_queryset()
        serializer = self.get_serializer(services, many=True)
        
        overall_status = all(service.status for service in services)
        
        data = {
            'status': 'healthy' if overall_status else 'degraded',
            'services': serializer.data,
            'timestamp': timezone.now().isoformat()
        }
        
        return success_response(data=data)

class BaseModelViewSet(viewsets.ModelViewSet):
    """
    Base viewset with common functionality
    """
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.is_staff:
            return self.queryset
        return self.queryset.filter(is_active=True)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    @action(detail=False, methods=['get'])
    def active(self, request):
        queryset = self.get_queryset().filter(is_active=True)
        serializer = self.get_serializer(queryset, many=True)
        return success_response(data=serializer.data)

    @action(detail=False, methods=['get'])
    def inactive(self, request):
        if not request.user.is_staff:
            return error_response(
                message="Permission denied",
                status_code=status.HTTP_403_FORBIDDEN
            )
        queryset = self.get_queryset().filter(is_active=False)
        serializer = self.get_serializer(queryset, many=True)
        return success_response(data=serializer.data)
    
# Admin Statistics View
@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_stats(request):
    """
    Get admin dashboard statistics
    """
    try:
        # Get total counts
        total_courses = Course.objects.count()
        total_users = User.objects.count()
        total_enrollments = Enrollment.objects.count()
        
        print(f"Total enrollments found: {total_enrollments}")  # Debug log
        
        # Get recent enrollments (last 7 days) with related data
        seven_days_ago = timezone.now() - timedelta(days=7)
        recent_enrollments = Enrollment.objects.select_related(
            'student', 'course'
        ).filter(
            enrolled_at__gte=seven_days_ago
        ).order_by('-enrolled_at')[:10]
        
        print(f"Recent enrollments (7 days): {recent_enrollments.count()}")  # Debug log
        
        # If no recent enrollments, get the most recent ones regardless of date
        if not recent_enrollments.exists():
            recent_enrollments = Enrollment.objects.select_related(
                'student', 'course'
            ).order_by('-enrolled_at')[:10]
            print(f"All recent enrollments: {recent_enrollments.count()}")  # Debug log
        
        # Get upcoming events (next 30 days)
        thirty_days_from_now = timezone.now() + timedelta(days=30)
        upcoming_events = CalendarEvent.objects.select_related(
            'course', 'course__instructor'
        ).filter(
            start_time__gte=timezone.now(),
            start_time__lte=thirty_days_from_now,
            status='scheduled'
        ).order_by('start_time')[:10]
        
        # Serialize recent enrollments
        recent_enrollments_data = []
        for enrollment in recent_enrollments:
            recent_enrollments_data.append({
                'id': str(enrollment.id),  # Convert UUID to string
                'studentId': str(enrollment.student.id),
                'courseId': str(enrollment.course.id),
                'enrolledAt': enrollment.enrolled_at.isoformat(),
                'completed': enrollment.completed,
                'progressPercentage': enrollment.progress_percentage,
                'student': {
                    'id': str(enrollment.student.id),
                    'name': enrollment.student.display_name,
                    'email': enrollment.student.email
                },
                'course': {
                    'id': str(enrollment.course.id),
                    'title': enrollment.course.title
                }
            })
        
        # Serialize upcoming events
        upcoming_events_data = []
        for event in upcoming_events:
            upcoming_events_data.append({
                'id': str(event.id),
                'title': event.title,
                'description': event.description,
                'eventType': event.event_type,
                'courseId': str(event.course.id) if event.course else None,
                'startTime': event.start_time.isoformat(),
                'endTime': event.end_time.isoformat() if event.end_time else None,
                'isAllDay': event.is_all_day,
                'status': event.status,
                'priority': event.priority,
                'attendees': [str(user.id) for user in event.attendees.all()],
                'location': event.location,
                'meetingUrl': event.meeting_url,
                'createdAt': event.created_at.isoformat(),
                'updatedAt': event.updated_at.isoformat(),
                'createdBy': str(event.created_by.id),
                'course': {
                    'id': str(event.course.id),
                    'title': event.course.title,
                    'color': getattr(event.course, 'color', '#3B82F6'),
                    'instructor': event.course.instructor.display_name,
                    'studentsEnrolled': event.course.enrollments.count(),
                    'status': 'published' if event.course.is_published else 'draft'
                } if event.course else None
            })
        
        stats_data = {
            'totalCourses': total_courses,
            'totalUsers': total_users,
            'totalEnrollments': total_enrollments,
            'recentEnrollments': recent_enrollments_data,
            'upcomingEvents': upcoming_events_data
        }
        
        print(f"Returning stats with {len(recent_enrollments_data)} recent enrollments")  # Debug log
        
        return Response(stats_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        print(f"Error in admin_stats: {str(e)}")  # Debug log
        return Response(
            {'error': f'Failed to fetch admin stats: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
