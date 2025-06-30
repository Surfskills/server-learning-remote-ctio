from rest_framework import viewsets, generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.decorators import action
from django.db.models import Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Count, Sum
from django.utils import timezone
from datetime import timedelta
from enrollments.models import Enrollment, CourseProgress
from courses.models import Course, Lecture
from users.models import UserActivity
from courses.serializers import CourseSerializer
from users.serializers import UserActivitySerializer

from .models import Enrollment, CourseProgress
from .serializers import (
    EnrollmentSerializer, 
    CourseProgressSerializer,
    EnrollmentCreateSerializer
)
from core.views import BaseModelViewSet
from core.utils import success_response, error_response
from core.permissions import IsStudent, IsEnrolledStudent

class EnrollmentViewSet(BaseModelViewSet):
    serializer_class = EnrollmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Enrollment.objects.select_related('student', 'course')
        
        # Regular users only see their own enrollments
        if not self.request.user.is_staff:
            queryset = queryset.filter(student=self.request.user)

        # Recent filter for query param approach
        if self.request.query_params.get('recent', '').lower() in ('true', '1', 'yes'):
            from datetime import datetime, timedelta
            thirty_days_ago = datetime.now() - timedelta(days=30)
            queryset = queryset.filter(enrolled_at__gte=thirty_days_ago)

        return queryset.order_by('-enrolled_at')
    
    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Optimized recent enrollments endpoint with custom logic"""
        queryset = self.filter_queryset(self.get_queryset())
        
        # More optimized than the query param approach
        from datetime import datetime, timedelta
        thirty_days_ago = datetime.now() - timedelta(days=30)
        recent_enrollments = queryset.filter(enrolled_at__gte=thirty_days_ago)
        
        page = self.paginate_queryset(recent_enrollments)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(recent_enrollments, many=True)
        return Response(serializer.data)

    def get_serializer_class(self):
        if self.action == 'create':
            return EnrollmentCreateSerializer
        return super().get_serializer_class()

    def perform_create(self, serializer):
        serializer.save(student=self.request.user)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        enrollment = self.get_object()
        if enrollment.student != request.user and not request.user.is_staff:
            return error_response("Permission denied", status_code=status.HTTP_403_FORBIDDEN)
        
        enrollment.completed = True
        enrollment.save()
        return success_response("Course marked as completed")

class CourseProgressViewSet(BaseModelViewSet):
    serializer_class = CourseProgressSerializer
    permission_classes = [IsAuthenticated, IsEnrolledStudent]

    def get_queryset(self):
        return CourseProgress.objects.filter(enrollment__student=self.request.user)

    def get_object(self):
        """
        Override to handle both CourseProgress ID and Enrollment ID
        """
        lookup_value = self.kwargs[self.lookup_field]
        
        # First try to get by CourseProgress ID
        try:
            return CourseProgress.objects.get(
                id=lookup_value,
                enrollment__student=self.request.user
            )
        except CourseProgress.DoesNotExist:
            # If not found, try to get by Enrollment ID
            try:
                enrollment = Enrollment.objects.get(
                    id=lookup_value,
                    student=self.request.user
                )
                # Get or create the CourseProgress
                progress, created = CourseProgress.objects.get_or_create(
                    enrollment=enrollment
                )
                return progress
            except Enrollment.DoesNotExist:
                raise CourseProgress.DoesNotExist("No CourseProgress matches the given query.")

    @action(detail=True, methods=['post'])
    def complete_lecture(self, request, pk=None):
        progress = self.get_object()
        lecture_id = request.data.get('lecture_id')
        
        if not lecture_id:
            return error_response('lecture_id is required', status_code=status.HTTP_400_BAD_REQUEST)
        
        try:
            lecture = Lecture.objects.get(pk=lecture_id)
            if lecture.section.course != progress.enrollment.course:
                return error_response('Lecture does not belong to this course', status_code=status.HTTP_400_BAD_REQUEST)
            
            # Add the lecture to completed lectures (signal will update progress automatically)
            progress.completed_lectures.add(lecture)
            
            # Get updated progress stats
            progress_stats = progress.get_progress_stats()
            
            response_data = {
                'progress_percentage': progress_stats['progress_percentage'],
                'completed_lectures_count': progress_stats['completed_lectures'],
                'total_lectures': progress_stats['total_lectures'],
                'remaining_lectures': progress_stats['remaining_lectures'],
                'message': 'Lecture marked as completed'
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
        except Lecture.DoesNotExist:
            return error_response('Lecture not found', status_code=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'])
    def uncomplete_lecture(self, request, pk=None):
        """Remove a lecture from completed lectures"""
        progress = self.get_object()
        lecture_id = request.data.get('lecture_id')
        
        if not lecture_id:
            return error_response('lecture_id is required', status_code=status.HTTP_400_BAD_REQUEST)
        
        try:
            lecture = Lecture.objects.get(pk=lecture_id)
            if lecture.section.course != progress.enrollment.course:
                return error_response('Lecture does not belong to this course', status_code=status.HTTP_400_BAD_REQUEST)
            
            # Remove the lecture from completed lectures (signal will update progress automatically)
            progress.completed_lectures.remove(lecture)
            
            # Get updated progress stats
            progress_stats = progress.get_progress_stats()
            
            response_data = {
                'progress_percentage': progress_stats['progress_percentage'],
                'completed_lectures_count': progress_stats['completed_lectures'],
                'total_lectures': progress_stats['total_lectures'],
                'remaining_lectures': progress_stats['remaining_lectures'],
                'message': 'Lecture marked as incomplete'
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
        except Lecture.DoesNotExist:
            return error_response('Lecture not found', status_code=status.HTTP_404_NOT_FOUND)

class AdminEnrollmentViewSet(BaseModelViewSet):
    """Admin-only viewset to see all enrollments"""
    serializer_class = EnrollmentSerializer
    permission_classes = [IsAdminUser]
    queryset = Enrollment.objects.select_related('student', 'course')
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filtering options
        course_id = self.request.query_params.get('course_id')
        if course_id:
            queryset = queryset.filter(course_id=course_id)
            
        student_id = self.request.query_params.get('student_id')
        if student_id:
            queryset = queryset.filter(student_id=student_id)
            
        # Date filtering
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(enrolled_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(enrolled_at__lte=end_date)
            
        return queryset.order_by('-enrolled_at')

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def student_dashboard(request):
    # Get enrolled courses with progress - use left join to include enrollments without progress
    enrollments = Enrollment.objects.filter(student=request.user).select_related(
        'course'
    ).prefetch_related(
        'course__sections__lectures',
        'progress'
    )
    
    enrolled_courses = []
    for enrollment in enrollments:
        # Handle missing progress gracefully
        try:
            progress = enrollment.progress
        except CourseProgress.DoesNotExist:
            # Create progress if it doesn't exist
            progress = CourseProgress.objects.create(enrollment=enrollment)
        
        course = enrollment.course
        
        # Get progress stats using the new method
        progress_stats = progress.get_progress_stats()
        
        enrolled_courses.append({
            'course': CourseSerializer(course).data,
            'progress': CourseProgressSerializer(progress).data,
            'enrollment': EnrollmentSerializer(enrollment).data,
            'progress_stats': progress_stats  # Add detailed stats
        })
    
    # Get learning stats
    total_courses = enrollments.count()
    completed_courses = enrollments.filter(completed=True).count()
    
    # Calculate total learning hours (sum of all course durations)
    total_hours = enrollments.aggregate(
        total=Sum('course__duration')
    )['total'] or 0
    total_hours = round(total_hours / 60)  # Convert minutes to hours
    
    # Get streak (simplified - count consecutive days with activity)
    today = timezone.now().date()
    streak_days = 0
    current_date = today
    while UserActivity.objects.filter(
        user=request.user,
        created_at__date=current_date
    ).exists():
        streak_days += 1
        current_date -= timedelta(days=1)
    
    # Get badges/achievements (simplified)
    badges = []
    if completed_courses > 0:
        badges.append({
            'id': '1',
            'name': 'First Course Completed',
            'description': 'Completed your first course',
            'imageUrl': '',
            'earnedDate': timezone.now().isoformat(),
            'category': 'milestone'
        })
    
    # Get recent activity
    recent_activity = UserActivity.objects.filter(
        user=request.user
    ).order_by('-created_at')[:5]
    
    data = {
        'enrolled_courses': enrolled_courses,
        'badges': badges,
        'stats': {
            'total_courses': total_courses,
            'completed_courses': completed_courses,
            'total_hours': total_hours,
            'streak_days': streak_days,
            'total_points': request.user.extended_profile.points or 0,
            'leaderboard_rank': None  # Implement leaderboard logic if needed
        },
        'recent_activity': UserActivitySerializer(recent_activity, many=True).data
    }
    
    return Response(data)