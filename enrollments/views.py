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
from django.shortcuts import get_object_or_404
from django.http import Http404
import logging
logger = logging.getLogger(__name__)
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.decorators import action
from rest_framework import status
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Count, Q
from enrollments.models import Enrollment, CourseProgress
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

    @action(detail=False, methods=['get'])
    def completed(self, request):
        """Get all completed courses for the current user"""
        completed_enrollments = self.get_queryset().filter(completed=True)
        
        page = self.paginate_queryset(completed_enrollments)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(completed_enrollments, many=True)
        return Response(serializer.data)

    def get_serializer_class(self):
        if self.action == 'create':
            return EnrollmentCreateSerializer
        return super().get_serializer_class()

    def perform_create(self, serializer):
        serializer.save(student=self.request.user)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Manually mark course as completed (admin override)"""
        enrollment = self.get_object()
        if enrollment.student != request.user and not request.user.is_staff:
            return error_response("Permission denied", status_code=status.HTTP_403_FORBIDDEN)
        
        enrollment.completed = True
        enrollment.completed_at = timezone.now()
        enrollment.save()
        
        # Award points if not already awarded
        if not enrollment.completed:
            enrollment._award_completion_points()
        
        return success_response("Course manually marked as completed")

    @action(detail=True, methods=['post'])
    def uncomplete(self, request, pk=None):
        """Manually mark course as incomplete (admin override)"""
        enrollment = self.get_object()
        if not request.user.is_staff:
            return error_response("Permission denied", status_code=status.HTTP_403_FORBIDDEN)
        
        enrollment.completed = False
        enrollment.completed_at = None
        enrollment.save()
        
        return success_response("Course marked as incomplete")

# enrollments/views.py
class CourseProgressViewSet(BaseModelViewSet):
    serializer_class = CourseProgressSerializer
    permission_classes = [IsAuthenticated, IsEnrolledStudent]
    lookup_field = 'enrollment_id'  # Make it clear we're looking up by enrollment

    def get_queryset(self):
        return CourseProgress.objects.filter(enrollment__student=self.request.user)

    def get_object(self):
        """Get progress by enrollment ID"""
        enrollment_id = self.kwargs.get('enrollment_id') or self.kwargs.get('pk')
        
        try:
            # Get enrollment and ensure user owns it
            enrollment = get_object_or_404(
                Enrollment,
                id=enrollment_id,
                student=self.request.user
            )
            
            # Get or create progress for this enrollment
            progress, created = CourseProgress.objects.get_or_create(
                enrollment=enrollment
            )
            
            if created:
                logger.info(f"Created new progress for enrollment {enrollment_id}")
            
            return progress
            
        except Exception as e:
            logger.error(f"Error getting progress for enrollment {enrollment_id}: {e}")
            raise Http404("Progress not found")
    @action(detail=True, methods=['post'])
    def complete_lecture(self, request, enrollment_id=None):
        """Mark lecture as completed"""
        try:
            progress = self.get_object()
            lecture_id = request.data.get('lecture_id')
            
            if not lecture_id:
                return error_response(
                    {'lecture_id': 'This field is required.'}, 
                    status.HTTP_400_BAD_REQUEST
                )

            # Get lecture and verify it belongs to the enrolled course
            try:
                lecture = Lecture.objects.select_related('section__course').get(
                    id=lecture_id
                )
                
                # Verify lecture belongs to the enrolled course
                if lecture.section.course_id != progress.enrollment.course_id:
                    return error_response(
                        {'lecture_id': f'Lecture does not belong to the enrolled course'},
                        status.HTTP_400_BAD_REQUEST
                    )
                
            except Lecture.DoesNotExist:
                return error_response(
                    {'lecture_id': 'Lecture not found'},
                    status.HTTP_404_NOT_FOUND
                )
            
            # Mark lecture as complete
            was_completed = progress.mark_lecture_complete(lecture)
            if not was_completed:
                return success_response({
                    'message': 'Lecture already completed',
                    'progress': progress.get_progress_stats()
                })
            
            progress_stats = progress.get_progress_stats()
            response_data = {
                'progress': progress_stats,
                'lecture': {
                    'id': lecture.id,
                    'title': lecture.title,
                    'section_id': lecture.section_id,
                    'course_id': lecture.section.course_id
                },
                'message': 'Lecture marked as completed'
            }
            
            if progress_stats['is_completed']:
                response_data['message'] = 'Course completed! Congratulations!'
            
            return success_response(response_data)
            
        except Exception as e:
            logger.exception("Error completing lecture")
            return error_response(
                {'error': f'Internal server error: {str(e)}'},
                status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def uncomplete_lecture(self, request, enrollment_id=None):
        """Remove a lecture from completed lectures"""
        progress = self.get_object()
        lecture_id = request.data.get('lecture_id')
        
        if not lecture_id:
            return error_response('lecture_id is required', status_code=status.HTTP_400_BAD_REQUEST)
        
        try:
            lecture = Lecture.objects.get(pk=lecture_id)
            
            # Use the new method
            progress.mark_lecture_incomplete(lecture)
            
            # Get updated progress stats
            progress_stats = progress.get_progress_stats()
            
            response_data = {
                'progress_percentage': progress_stats['progress_percentage'],
                'completed_lectures_count': progress_stats['completed_lectures'],
                'total_lectures': progress_stats['total_lectures'],
                'remaining_lectures': progress_stats['remaining_lectures'],
                'is_course_completed': progress_stats['is_completed'],
                'course_completed_at': progress.enrollment.completed_at.isoformat() if progress.enrollment.completed_at else None,
                'message': 'Lecture marked as incomplete'
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
        except Lecture.DoesNotExist:
            return error_response('Lecture not found', status_code=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['get'])
    def progress_detail(self, request, enrollment_id=None):
        """Get detailed progress information"""
        progress = self.get_object()
        progress_stats = progress.get_progress_stats()
        
        # Get completed lectures with details
        completed_lectures = progress.completed_lectures.select_related('section').all()
        
        response_data = {
            'enrollment': EnrollmentSerializer(progress.enrollment).data,
            'progress_stats': progress_stats,
            'completed_lectures': [
                {
                    'id': lecture.id,
                    'title': lecture.title,
                    'section': lecture.section.title,
                    'order': lecture.order
                }
                for lecture in completed_lectures
            ],
            'last_accessed_lecture': {
                'id': progress.last_accessed_lecture.id,
                'title': progress.last_accessed_lecture.title,
                'section': progress.last_accessed_lecture.section.title
            } if progress.last_accessed_lecture else None
        }
        
        return Response(response_data, status=status.HTTP_200_OK)

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
            
        # Completion status filter
        completed = self.request.query_params.get('completed')
        if completed is not None:
            queryset = queryset.filter(completed=completed.lower() in ('true', '1', 'yes'))
            
        # Date filtering
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(enrolled_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(enrolled_at__lte=end_date)
            
        return queryset.order_by('-enrolled_at')

    @action(detail=False, methods=['get'])
    def completion_stats(self, request):
        """Get course completion statistics"""
        queryset = self.get_queryset()
        
        total_enrollments = queryset.count()
        completed_enrollments = queryset.filter(completed=True).count()
        completion_rate = (completed_enrollments / total_enrollments * 100) if total_enrollments > 0 else 0
        
        # Get completion stats by course
        course_stats = queryset.values('course__title').annotate(
            total_enrollments=Count('id'),
            completed_enrollments=Count('id', filter=Q(completed=True))
        ).order_by('-total_enrollments')
        
        for stat in course_stats:
            total = stat['total_enrollments']
            completed = stat['completed_enrollments']
            stat['completion_rate'] = (completed / total * 100) if total > 0 else 0
        
        return Response({
            'overall_stats': {
                'total_enrollments': total_enrollments,
                'completed_enrollments': completed_enrollments,
                'completion_rate': round(completion_rate, 2)
            },
            'course_stats': course_stats
        })

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
            'progress_stats': progress_stats,  # Add detailed stats
            'is_completed': enrollment.completed,
            'completed_at': enrollment.completed_at.isoformat() if enrollment.completed_at else None
        })
    
    # Get learning stats
    total_courses = enrollments.count()
    completed_courses = enrollments.filter(completed=True).count()
    in_progress_courses = enrollments.filter(completed=False).count()
    
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
    
    # Get badges/achievements (enhanced)
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
    
    if completed_courses >= 5:
        badges.append({
            'id': '2',
            'name': 'Learning Enthusiast',
            'description': 'Completed 5 courses',
            'imageUrl': '',
            'earnedDate': timezone.now().isoformat(),
            'category': 'achievement'
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
            'in_progress_courses': in_progress_courses,
            'total_hours': total_hours,
            'streak_days': streak_days,
            'total_points': request.user.extended_profile.points or 0,
            'completion_rate': round((completed_courses / total_courses * 100), 2) if total_courses > 0 else 0,
            'leaderboard_rank': None  # Implement leaderboard logic if needed
        },
        'recent_activity': UserActivitySerializer(recent_activity, many=True).data
    }
    
    return Response(data)