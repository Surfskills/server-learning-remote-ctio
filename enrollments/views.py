# enrollments/views.py
from datetime import datetime, timedelta
from rest_framework.views import APIView
from django.db.models import Q, Count, Sum
from django.shortcuts import get_object_or_404
from django.http import Http404
from django.utils import timezone
from rest_framework import viewsets, generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response 
from core import permissions
from enrollments.models import Enrollment, CourseProgress
from courses.models import Course, Lecture
from payments.models import Order
from users.models import UserActivity
from courses.serializers import CourseSerializer
from users.serializers import UserActivitySerializer
from .serializers import (
    EnrollmentSerializer, 
    CourseProgressSerializer,
    EnrollmentCreateSerializer
)
from rest_framework.decorators import action
from django.db.models import Count, Avg, Q, Sum
from core.views import BaseModelViewSet
from core.utils import success_response, error_response
from core.permissions import (
    IsStudent, 
    CanManageEnrollments,
    CanAccessCourseContent,
    IsAdminUser as CoreIsAdminUser
)


class IsEnrolledStudent(permissions.BasePermission):
    """
    Permission to check if the user is a student enrolled in the course.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
            
        # Admin users have full access
        if request.user.is_staff or request.user.is_superuser:
            return True
            
        # Must be a student
        if not request.user.is_student:
            return False
            
        # For enrollment-specific actions
        enrollment_id = view.kwargs.get('enrollment_id') or view.kwargs.get('pk')
        if enrollment_id:
            try:
                enrollment = Enrollment.objects.get(pk=enrollment_id)
                return enrollment.student == request.user
            except Enrollment.DoesNotExist:
                return False
                
        return True
    
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
            
        # Admin users have full access
        if request.user.is_staff or request.user.is_superuser:
            return True
            
        # Get the enrollment from the object
        enrollment = self._get_enrollment_from_object(obj)
        if not enrollment:
            return False
            
        return enrollment.student == request.user
    
    def _get_enrollment_from_object(self, obj):
        """Extract enrollment from various object types."""
        if hasattr(obj, 'student'):  # Direct enrollment object
            return obj
        if hasattr(obj, 'enrollment'):  # Objects with enrollment attribute
            return obj.enrollment
        return None


class EnrollmentViewSet(BaseModelViewSet):
    serializer_class = EnrollmentSerializer
    permission_classes = [IsAuthenticated, CanManageEnrollments]

    def get_queryset(self):
        queryset = Enrollment.objects.select_related('student', 'course')
        
        # Admin users can see all enrollments
        if self.request.user.is_staff or self.request.user.is_superuser:
            return queryset
        
        # Instructors can see enrollments in their courses only
        elif self.request.user.user_type == 'INSTRUCTOR':
            queryset = queryset.filter(course__instructor=self.request.user)
        
        # Students see only their own enrollments
        else:
            queryset = queryset.filter(student=self.request.user)

        # Apply additional filters after role-based filtering
        # Filter by course_id if provided
        course_id = self.request.query_params.get('course_id')
        if course_id:
            queryset = queryset.filter(course_id=course_id)

        # Filter by course_slug if provided
        course_slug = self.request.query_params.get('course_slug')
        if course_slug:
            queryset = queryset.filter(course__slug=course_slug)

        # Recent filter for query param approach
        if self.request.query_params.get('recent', '').lower() in ('true', '1', 'yes'):
            thirty_days_ago = datetime.now() - timedelta(days=30)
            queryset = queryset.filter(enrolled_at__gte=thirty_days_ago)

        return queryset.order_by('-enrolled_at')

    @action(detail=False, methods=['get'])
    def by_course(self, request):
        """Get enrollment for a specific course"""
        course_id = request.query_params.get('course_id')
        course_slug = request.query_params.get('course_slug')
        
        if not course_id and not course_slug:
            return error_response(
                "Either course_id or course_slug is required",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            queryset = self.get_queryset()
            
            if course_id:
                enrollment = queryset.filter(course_id=course_id).first()
            else:
                enrollment = queryset.filter(course__slug=course_slug).first()
            
            if not enrollment:
                return error_response(
                    "No enrollment found for this course",
                    status_code=status.HTTP_404_NOT_FOUND
                )
            
            serializer = self.get_serializer(enrollment)
            return success_response(
                data=serializer.data,
                message="Enrollment retrieved successfully"
            )
            
        except Exception as e:
            return error_response(
                "Failed to retrieve enrollment",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Optimized recent enrollments endpoint with custom logic"""
        queryset = self.filter_queryset(self.get_queryset())
        
        # More optimized than the query param approach
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


class CourseProgressViewSet(BaseModelViewSet):
    serializer_class = CourseProgressSerializer
    permission_classes = [IsAuthenticated, IsEnrolledStudent]
    lookup_field = 'enrollment_id'

    def get_queryset(self):
        queryset = CourseProgress.objects.select_related(
            'enrollment__student',
            'enrollment__course'
        )
        
        # Admin sees all progress
        if self.request.user.is_staff:
            return queryset
        
        # Instructors see progress for their courses
        if self.request.user.user_type == 'INSTRUCTOR':
            return queryset.filter(
                enrollment__course__instructor=self.request.user
            )
        
        # Students see only their own progress
        return queryset.filter(enrollment__student=self.request.user)

    def get_object(self):
        """Get progress by enrollment ID"""
        enrollment_id = self.kwargs.get('enrollment_id') or self.kwargs.get('pk')
        
        try:
            # Get enrollment and ensure user owns it or has permission
            if self.request.user.is_staff or self.request.user.is_superuser:
                enrollment = get_object_or_404(Enrollment, id=enrollment_id)
            elif self.request.user.user_type == 'INSTRUCTOR':
                enrollment = get_object_or_404(
                    Enrollment,
                    id=enrollment_id,
                    course__instructor=self.request.user
                )
            else:
                enrollment = get_object_or_404(
                    Enrollment,
                    id=enrollment_id,
                    student=self.request.user
                )
            
            # Get or create progress for this enrollment
            progress, created = CourseProgress.objects.get_or_create(
                enrollment=enrollment
            )
            
            return progress
            
        except Exception as e:
            raise Http404("Progress not found")

    @action(detail=True, methods=['post'])
    def complete_lecture(self, request, enrollment_id=None):
        """Mark lecture as completed with enhanced validation"""
        try:
            # Get progress object and validate enrollment belongs to user
            progress = self.get_object()
            lecture_id = request.data.get('lecture_id')
            course_id = request.data.get('course_id')
            section_id = request.data.get('section_id')
            lecture_title = request.data.get('lecture_title')
            section_title = request.data.get('section_title')
            
            if not lecture_id:
                return error_response(
                    {'lecture_id': 'This field is required.'}, 
                    status.HTTP_400_BAD_REQUEST
                )

            # Get enrollment from progress
            enrollment = progress.enrollment
            
            # Validate enrollment belongs to the user (unless admin/instructor)
            if not self.request.user.is_staff and not self.request.user.is_superuser:
                if self.request.user.user_type == 'INSTRUCTOR':
                    if enrollment.course.instructor != self.request.user:
                        return error_response(
                            {'error': 'You are not authorized to manage this enrollment'},
                            status.HTTP_403_FORBIDDEN
                        )
                else:
                    if enrollment.student != self.request.user:
                        return error_response(
                            {'error': 'You are not authorized to complete lectures for this enrollment'},
                            status.HTTP_403_FORBIDDEN
                        )

            # Validate course_id matches enrollment if provided
            if course_id and str(enrollment.course_id) != str(course_id):
                return error_response(
                    {'course_id': f'Course ID mismatch. Expected {enrollment.course_id}, got {course_id}'},
                    status.HTTP_400_BAD_REQUEST
                )

            # Get lecture with enhanced validation
            try:
                lecture = Lecture.objects.select_related('section__course').get(
                    id=lecture_id
                )
                
                # Validate lecture belongs to the enrolled course
                if lecture.section.course_id != enrollment.course_id:
                    return error_response(
                        {'lecture_id': f'Lecture does not belong to the enrolled course. Expected course {enrollment.course_id}, but lecture belongs to course {lecture.section.course_id}'},
                        status.HTTP_400_BAD_REQUEST
                    )
                
                # Validate section_id matches if provided
                if section_id and str(lecture.section_id) != str(section_id):
                    return error_response(
                        {'section_id': f'Section ID mismatch. Lecture belongs to section {lecture.section_id}, but {section_id} was provided'},
                        status.HTTP_400_BAD_REQUEST
                    )

                # Additional validation - check if lecture is part of course structure
                course = lecture.section.course
                if not course.sections.filter(id=lecture.section_id).exists():
                    return error_response(
                        {'lecture_id': 'Lecture section not found in course structure'},
                        status.HTTP_400_BAD_REQUEST
                    )

                # Validate course is active/published
                if not course.is_published:
                    return error_response(
                        {'course_id': 'Cannot complete lectures in unpublished courses'},
                        status.HTTP_400_BAD_REQUEST
                    )
                    
                # Check if lecture is already completed
                if progress.completed_lectures.filter(id=lecture_id).exists():
                    return Response({
                        'status': 'success',
                        'message': 'Lecture already completed',
                        'data': {
                            'progress_percentage': progress.get_progress_percentage(),
                            'completed_lectures': list(progress.completed_lectures.values_list('id', flat=True)),
                            'lecture_completed': True,
                            'is_course_completed': progress.is_course_completed()
                        }
                    }, status=status.HTTP_200_OK)
                
                # Mark lecture as complete
                was_completed = progress.mark_lecture_complete(lecture)
                if not was_completed:
                    return Response({
                        'status': 'success',
                        'message': 'Lecture already completed',
                        'data': {
                            'progress_percentage': progress.get_progress_percentage(),
                            'completed_lectures': list(progress.completed_lectures.values_list('id', flat=True)),
                            'is_course_completed': progress.is_course_completed()
                        }
                    }, status=status.HTTP_200_OK)
                
                # Prepare response data
                response_data = {
                    'status': 'success',
                    'message': 'Lecture marked as completed',
                    'data': {
                        'progress_percentage': progress.get_progress_percentage(),
                        'completed_lectures': list(progress.completed_lectures.values_list('id', flat=True)),
                        'lecture_completed': True,
                        'is_course_completed': progress.is_course_completed(),
                        'last_accessed_lecture_id': lecture.id,
                        'enrollment_id': enrollment.id,
                        'course_id': enrollment.course_id
                    },
                    'lecture': {
                        'id': lecture.id,
                        'title': lecture_title or lecture.title,
                        'section_id': lecture.section_id,
                        'section_title': section_title or lecture.section.title,
                        'course_id': lecture.section.course_id,
                        'order': lecture.order
                    }
                }
                
                # Check if course is now completed
                if progress.is_course_completed() and not enrollment.completed:
                    enrollment.completed = True
                    enrollment.completed_at = timezone.now()
                    enrollment.save()
                    
                    if hasattr(enrollment, '_award_completion_points'):
                        enrollment._award_completion_points()
                    
                    response_data['message'] = 'Course completed! Congratulations!'
                    response_data['data']['course_completed_at'] = enrollment.completed_at.isoformat()
                
                return Response(response_data, status=status.HTTP_200_OK)
                
            except Lecture.DoesNotExist:
                return error_response(
                    {'lecture_id': 'Lecture not found'},
                    status.HTTP_404_NOT_FOUND
                )
                
        except Exception as e:
            return error_response(
                {'error': f'Internal server error: {str(e)}'},
                status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def uncomplete_lecture(self, request, enrollment_id=None):
        """Remove a lecture from completed lectures"""
        try:
            progress = self.get_object()
            lecture_id = request.data.get('lecture_id')
            
            if not lecture_id:
                return error_response('lecture_id is required', status_code=status.HTTP_400_BAD_REQUEST)
            
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
        except Exception as e:
            return error_response(
                f'Internal server error: {str(e)}',
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def progress_detail(self, request, enrollment_id=None):
        """Get detailed progress information"""
        try:
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
            
        except Exception as e:
            return error_response(
                f'Internal server error: {str(e)}',
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AdminEnrollmentViewSet(BaseModelViewSet):
    """Admin-only viewset to see all enrollments"""
    serializer_class = EnrollmentSerializer
    permission_classes = [CoreIsAdminUser]
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
        try:
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
            
        except Exception as e:
            return error_response(
                f'Internal server error: {str(e)}',
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )



def get_user_badges(user, completed_courses_count):
    """Enhanced badge system with exciting achievements using React icons"""
    badges = []
    
    # Course completion badges with engaging descriptions
    if completed_courses_count >= 1:
        badges.append({
            'id': 'first_course',
            'name': '🎯 First Victory',
            'description': 'Conquered your first course! The journey begins.',
            'icon': 'Target',
            'iconColor': '#10B981',  # emerald-500
            'earnedDate': timezone.now().isoformat(),
            'category': 'milestone',
            'rarity': 'common',
            'points': 100
        })
    
    if completed_courses_count >= 2:
        badges.append({
            'id': 'double_achiever',
            'name': '🔥 Double Threat',
            'description': 'Two courses down! You\'re building momentum.',
            'icon': 'Flame',
            'iconColor': '#EF4444',  # red-500
            'earnedDate': timezone.now().isoformat(),
            'category': 'achievement',
            'rarity': 'uncommon',
            'points': 250
        })
    
    if completed_courses_count >= 3:
        badges.append({
            'id': 'triple_master',
            'name': '⚡ Triple Crown',
            'description': 'Three courses mastered! You\'re unstoppable.',
            'icon': 'Zap',
            'iconColor': '#F59E0B',  # amber-500
            'earnedDate': timezone.now().isoformat(),
            'category': 'achievement',
            'rarity': 'rare',
            'points': 500
        })
    
    if completed_courses_count >= 4:
        badges.append({
            'id': 'quad_legend',
            'name': '👑 Quad Legend',
            'description': 'Four courses conquered! You\'re a true learning champion.',
            'icon': 'Crown',
            'iconColor': '#8B5CF6',  # violet-500
            'earnedDate': timezone.now().isoformat(),
            'category': 'achievement',
            'rarity': 'epic',
            'points': 1000
        })
    
    if completed_courses_count >= 5:
        badges.append({
            'id': 'learning_enthusiast',
            'name': '🌟 Learning Enthusiast',
            'description': 'Five courses completed! Your dedication is inspiring.',
            'icon': 'Star',
            'iconColor': '#F59E0B',  # amber-500
            'earnedDate': timezone.now().isoformat(),
            'category': 'achievement',
            'rarity': 'legendary',
            'points': 2000
        })
    
    if completed_courses_count >= 10:
        badges.append({
            'id': 'knowledge_seeker',
            'name': '🚀 Knowledge Seeker',
            'description': 'Ten courses mastered! You\'re in the elite league.',
            'icon': 'Rocket',
            'iconColor': '#3B82F6',  # blue-500
            'earnedDate': timezone.now().isoformat(),
            'category': 'achievement',
            'rarity': 'legendary',
            'points': 5000
        })
    
    # Special achievement badges
    if completed_courses_count >= 3:
        badges.append({
            'id': 'consistency_king',
            'name': '💎 Consistency Champion',
            'description': 'Proven your commitment to continuous learning!',
            'icon': 'Gem',
            'iconColor': '#06B6D4',  # cyan-500
            'earnedDate': timezone.now().isoformat(),
            'category': 'special',
            'rarity': 'rare',
            'points': 750
        })
    
    return badges

def award_course_completion_badge(user, completed_courses_count):
    """Award special completion badges with celebrations"""
    celebration_messages = {
        1: "🎉 Congratulations! You've completed your first course!",
        2: "🔥 Amazing! Two courses down - you're on fire!",
        3: "⚡ Incredible! Three courses mastered - you're unstoppable!",
        4: "👑 Legendary! Four courses conquered - you're a true champion!",
        5: "🌟 Phenomenal! Five courses completed - you're an inspiration!"
    }
    
    special_rewards = {
        2: {"points": 250, "title": "Double Achiever"},
        3: {"points": 500, "title": "Triple Master", "unlock": "Advanced Learning Path"},
        4: {"points": 1000, "title": "Quad Legend", "unlock": "Premium Course Access"},
        5: {"points": 2000, "title": "Learning Enthusiast", "unlock": "Mentor Status"}
    }
    
    message = celebration_messages.get(completed_courses_count, "🎯 Another course completed!")
    reward = special_rewards.get(completed_courses_count, {})
    
    return {
        'celebration_message': message,
        'bonus_points': reward.get('points', 0),
        'new_title': reward.get('title'),
        'special_unlock': reward.get('unlock'),
        'show_celebration': completed_courses_count in [2, 3, 4, 5]
    }

def get_badge_icon_config():
    """Return icon configuration for frontend mapping"""
    return {
        'first_course': {'icon': 'Target', 'color': '#10B981'},
        'double_achiever': {'icon': 'Flame', 'color': '#EF4444'},
        'triple_master': {'icon': 'Zap', 'color': '#F59E0B'},
        'quad_legend': {'icon': 'Crown', 'color': '#8B5CF6'},
        'learning_enthusiast': {'icon': 'Star', 'color': '#F59E0B'},
        'knowledge_seeker': {'icon': 'Rocket', 'color': '#3B82F6'},
        'consistency_king': {'icon': 'Gem', 'color': '#06B6D4'}
    }

def get_available_icons():
    """Return list of available Lucide React icons used in badges"""
    return [
        'Target',    # 🎯 First course
        'Flame',     # 🔥 Double achiever
        'Zap',       # ⚡ Triple master
        'Crown',     # 👑 Quad legend
        'Star',      # 🌟 Learning enthusiast
        'Rocket',    # 🚀 Knowledge seeker
        'Gem',       # 💎 Consistency champion
        'Trophy',    # Additional option
        'Award',     # Additional option
        'Medal',     # Additional option
        'Shield',    # Additional option
        'Lightbulb', # Additional option
        'BookOpen',  # Additional option
        'GraduationCap' # Additional option
    ]

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def student_dashboard(request):
    """Student dashboard with enrollment and progress data"""
    try:
        # Get enrolled courses with progress
        enrollments = Enrollment.objects.filter(student=request.user).select_related(
            'course'
        ).prefetch_related(
            'course__sections__lectures',
            'progress'
        )
        
        enrolled_courses = []
        for enrollment in enrollments:
            try:
                progress = enrollment.progress
            except CourseProgress.DoesNotExist:
                progress = CourseProgress.objects.create(enrollment=enrollment)
            
            course = enrollment.course
            progress_stats = progress.get_progress_stats()
            
            enrolled_courses.append({
                'course': CourseSerializer(course).data,
                'progress': CourseProgressSerializer(progress).data,
                'enrollment': EnrollmentSerializer(enrollment).data,
                'progress_stats': progress_stats,
                'is_completed': enrollment.completed,
                'completed_at': enrollment.completed_at.isoformat() if enrollment.completed_at else None
            })
        
        # Get learning stats
        total_courses = enrollments.count()
        completed_courses = enrollments.filter(completed=True).count()
        in_progress_courses = enrollments.filter(completed=False).count()
        
        # Calculate total learning hours
        total_hours = enrollments.aggregate(
            total=Sum('course__duration')
        )['total'] or 0
        total_hours = round(total_hours / 60)
        
        # Get streak
        today = timezone.now().date()
        streak_days = 0
        current_date = today
        while UserActivity.objects.filter(
            user=request.user,
            created_at__date=current_date
        ).exists():
            streak_days += 1
            current_date -= timedelta(days=1)
        
        # Get enhanced badges
        badges = get_user_badges(request.user, completed_courses)
        
        # Get recent activity
        recent_activity = UserActivity.objects.filter(
            user=request.user
        ).order_by('-created_at')[:5]
        
        # Calculate achievement progress
        achievement_progress = {
            'next_milestone': 5 if completed_courses < 5 else 10,
            'courses_to_next': max(0, (5 if completed_courses < 5 else 10) - completed_courses),
            'progress_percentage': min(100, (completed_courses / (5 if completed_courses < 5 else 10)) * 100)
        }
        
        data = {
            'enrolled_courses': enrolled_courses,
            'badges': badges,
            'achievement_progress': achievement_progress,
            'stats': {
                'total_courses': total_courses,
                'completed_courses': completed_courses,
                'in_progress_courses': in_progress_courses,
                'total_hours': total_hours,
                'streak_days': streak_days,
                'total_points': request.user.extended_profile.points or 0,
                'completion_rate': round((completed_courses / total_courses * 100), 2) if total_courses > 0 else 0,
                'leaderboard_rank': None,
                'badges_earned': len(badges),
                'achievement_level': get_achievement_level(completed_courses)
            },
            'recent_activity': UserActivitySerializer(recent_activity, many=True).data
        }
        
        return Response(data)
        
    except Exception as e:
        return Response(
            {'error': f'Internal server error: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

def get_achievement_level(completed_courses):
    """Get user's achievement level based on completed courses"""
    if completed_courses >= 10:
        return {"level": "Master", "title": "🎓 Learning Master", "color": "#FFD700"}
    elif completed_courses >= 5:
        return {"level": "Expert", "title": "🌟 Learning Expert", "color": "#9370DB"}
    elif completed_courses >= 3:
        return {"level": "Advanced", "title": "⚡ Advanced Learner", "color": "#FF6B6B"}
    elif completed_courses >= 1:
        return {"level": "Intermediate", "title": "🔥 Rising Star", "color": "#4ECDC4"}
    else:
        return {"level": "Beginner", "title": "🎯 Getting Started", "color": "#95E1D3"}

class InstructorDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # First check if the user is actually an instructor
        if not request.user.user_type == 'INSTRUCTOR':
            return Response(
                {'error': 'Only instructors can access this dashboard'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            # Get total counts using the same approach as admin_stats
            total_courses = Course.objects.filter(instructor=request.user).count()
            total_enrollments = Enrollment.objects.filter(course__instructor=request.user).count()
            
            print(f"Total enrollments found for instructor: {total_enrollments}")  # Debug log
            
            # Get instructor's courses with stats
            courses = Course.objects.filter(
                instructor=request.user
            ).prefetch_related(
                'enrollments',
                'orders'
            ).annotate(
                total_students=Count('enrollments', distinct=True),
                active_students=Count(
                    'enrollments',
                    filter=Q(enrollments__last_accessed__gte=timezone.now()-timedelta(days=30)),
                    distinct=True
                ),
                completed_students=Count(
                    'enrollments',
                    filter=Q(enrollments__completed=True),
                    distinct=True
                ),
                total_earnings=Sum(
                    'orders__amount',
                    filter=Q(orders__status='paid'),
                    distinct=True
                )
            )

            # Debug output (remove in production)
            print(f"Instructor courses: {courses.count()}")
            for course in courses:
                print(f"Course {course.title}: {course.total_students} students")

            # Get recent enrollments (last 7 days) with related data - same as admin_stats
            seven_days_ago = timezone.now() - timedelta(days=7)
            recent_enrollments = Enrollment.objects.select_related(
                'student', 'course'
            ).filter(
                course__instructor=request.user,
                enrolled_at__gte=seven_days_ago
            ).order_by('-enrolled_at')[:10]
            
            print(f"Recent enrollments (7 days) for instructor: {recent_enrollments.count()}")  # Debug log
            
            # If no recent enrollments, get the most recent ones regardless of date
            if not recent_enrollments.exists():
                recent_enrollments = Enrollment.objects.select_related(
                    'student', 'course'
                ).filter(
                    course__instructor=request.user
                ).order_by('-enrolled_at')[:10]
                print(f"All recent enrollments for instructor: {recent_enrollments.count()}")  # Debug log

            # Get course progress stats
            course_progress = Enrollment.objects.filter(
                course__instructor=request.user
            ).values('course__title').annotate(
                avg_progress=Avg('progress_percentage'),
                avg_time_spent=Avg('time_spent_minutes')
            )

            # Get earnings data
            earnings = Order.objects.filter(
                course__instructor=request.user,
                status='paid'
            ).aggregate(
                total_earnings=Sum('amount'),
                monthly_earnings=Sum(
                    'amount',
                    filter=Q(completed_at__gte=timezone.now()-timedelta(days=30))
            ))

            # Calculate totals using the same approach as admin_stats
            totals = {
                'total_courses': total_courses,  # Direct count like admin_stats
                'total_enrollments': total_enrollments,  # Direct count like admin_stats
                'total_students': sum(course.total_students for course in courses),
                'active_students': sum(course.active_students for course in courses),
                'completed_students': sum(course.completed_students for course in courses),
                'total_earnings': earnings['total_earnings'] or 0,
                'monthly_earnings': earnings['monthly_earnings'] or 0
            }

            print(f"Returning instructor stats with {len(recent_enrollments)} recent enrollments")  # Debug log

            return Response({
                'totals': totals,
                'courses': CourseSerializer(courses, many=True).data,
                'recent_enrollments': EnrollmentSerializer(recent_enrollments, many=True).data,
                'course_progress': list(course_progress),
                'earnings': earnings
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            print(f"Error in instructor dashboard: {str(e)}")  # Debug log
            return Response(
                {'error': f'Failed to fetch instructor dashboard data: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )