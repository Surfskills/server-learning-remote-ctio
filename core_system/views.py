from rest_framework import viewsets, generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.decorators import action

# Add these to your existing views.py
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.decorators import action
from django.db.models import Count, Q
from .models import (
    CourseCategory, QaItem, ProjectTool, 
    QuizQuestion, QuizTask, GradingCriterion,
    SubmissionFile, TaskGrade, CriteriaGrade,
    Faq, Announcement, CalendarNotification,
    NotificationPreferences, CalendarPermissions,
    PlannedCourseRelease, DripSchedule, DripScheduleEntry
)
from .serializers import (
    CourseCategorySerializer, QaItemSerializer,
    ProjectToolSerializer, QuizQuestionSerializer,
    QuizTaskSerializer, GradingCriterionSerializer,
    SubmissionFileSerializer, TaskGradeSerializer,
    CriteriaGradeSerializer, FaqSerializer,
    AnnouncementSerializer, CalendarNotificationSerializer,
    NotificationPreferencesSerializer, CalendarPermissionsSerializer,
    PlannedCourseReleaseSerializer, DripScheduleSerializer,
    DripScheduleEntrySerializer
)

from django.db.models import Count, Avg
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



class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    # permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminUser()]
        return super().get_permissions()

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.is_staff:
            return queryset
        return queryset.filter(is_published=True)

    @action(detail=True, methods=['post'])
    def enroll(self, request, pk=None):
        course = self.get_object()
        if Enrollment.objects.filter(student=request.user, course=course).exists():
            return Response({'detail': 'Already enrolled'}, status=status.HTTP_400_BAD_REQUEST)
        
        enrollment = Enrollment.objects.create(
            student=request.user,
            course=course
        )
        CourseProgress.objects.create(enrollment=enrollment)
        return Response({'detail': 'Enrolled successfully'}, status=status.HTTP_201_CREATED)

class CourseSectionViewSet(viewsets.ModelViewSet):
    serializer_class = CourseSectionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        course_id = self.kwargs.get('course_pk')
        return CourseSection.objects.filter(course_id=course_id).order_by('order')

    def perform_create(self, serializer):
        course = Course.objects.get(pk=self.kwargs.get('course_pk'))
        serializer.save(course=course)

class LectureViewSet(viewsets.ModelViewSet):
    queryset = Lecture.objects.all()
    serializer_class = LectureSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        section_id = self.request.query_params.get('section_id')
        if section_id:
            queryset = queryset.filter(section_id=section_id)
        return queryset.order_by('order')

    def perform_create(self, serializer):
        section_id = self.request.data.get('section_id')
        last_lecture = Lecture.objects.filter(section_id=section_id).order_by('-order').first()
        new_order = (last_lecture.order + 1) if last_lecture else 1
        serializer.save(order=new_order)

class LectureResourceViewSet(viewsets.ModelViewSet):
    queryset = LectureResource.objects.all()
    serializer_class = LectureResourceSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        lecture_id = self.request.query_params.get('lecture_id')
        if lecture_id:
            queryset = queryset.filter(lecture_id=lecture_id)
        return queryset
    
class EnrollmentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = EnrollmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # If user is admin, show all enrollments
        if self.request.user.is_staff or self.request.user.is_superuser:
            queryset = Enrollment.objects.select_related('student', 'course').all().order_by('-enrolled_at')
        else:
            # Regular users only see their own enrollments
            queryset = Enrollment.objects.select_related('student', 'course').filter(
                student=self.request.user
            ).order_by('-enrolled_at')
        
        # Add filtering options
        course_id = self.request.query_params.get('course_id')
        if course_id:
            queryset = queryset.filter(course_id=course_id)
            
        return queryset
class AdminEnrollmentViewSet(viewsets.ReadOnlyModelViewSet):
    """Admin-only viewset to see all enrollments"""
    serializer_class = EnrollmentSerializer
    permission_classes = [IsAdminUser]
    
    def get_queryset(self):
        queryset = Enrollment.objects.select_related('student', 'course').all().order_by('-enrolled_at')
        
        # Add filtering options
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
            
        return queryset
    
class CourseProgressViewSet(viewsets.ModelViewSet):
    serializer_class = CourseProgressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return CourseProgress.objects.filter(enrollment__student=self.request.user)

    @action(detail=True, methods=['post'])
    def complete_lecture(self, request, pk=None):
        progress = self.get_object()
        lecture_id = request.data.get('lecture_id')
        if not lecture_id:
            return Response({'detail': 'lecture_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            lecture = Lecture.objects.get(pk=lecture_id)
            if lecture.section.course != progress.enrollment.course:
                return Response({'detail': 'Lecture does not belong to this course'}, status=status.HTTP_400_BAD_REQUEST)
            
            progress.completed_lectures.add(lecture)
            return Response({'detail': 'Lecture marked as completed'}, status=status.HTTP_200_OK)
        except Lecture.DoesNotExist:
            return Response({'detail': 'Lecture not found'}, status=status.HTTP_404_NOT_FOUND)

class ReviewViewSet(viewsets.ModelViewSet):
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        course_id = self.kwargs.get('course_pk')
        return Review.objects.filter(course_id=course_id)

    def perform_create(self, serializer):
        course = Course.objects.get(pk=self.kwargs.get('course_pk'))
        serializer.save(student=self.request.user, course=course)

class QuizViewSet(viewsets.ModelViewSet):
    serializer_class = QuizSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        course_id = self.kwargs.get('course_pk')
        return Quiz.objects.filter(course_id=course_id)

    def perform_create(self, serializer):
        course = Course.objects.get(pk=self.kwargs.get('course_pk'))
        serializer.save(course=course)

class QuizSubmissionViewSet(viewsets.ModelViewSet):
    serializer_class = QuizSubmissionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        quiz_id = self.kwargs.get('quiz_pk')
        return QuizSubmission.objects.filter(quiz_id=quiz_id, student=self.request.user)

    def perform_create(self, serializer):
        quiz = Quiz.objects.get(pk=self.kwargs.get('quiz_pk'))
        serializer.save(student=self.request.user, quiz=quiz)

class QuizGradeViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = QuizGradeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        quiz_id = self.kwargs.get('quiz_pk')
        return QuizGrade.objects.filter(quiz_id=quiz_id, student=self.request.user)

class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class CertificateViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CertificateSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Certificate.objects.filter(student=self.request.user)

class CalendarEventViewSet(viewsets.ModelViewSet):
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

class StudentProgressControlViewSet(viewsets.ModelViewSet):
    serializer_class = StudentProgressControlSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return StudentProgressControl.objects.filter(student=self.request.user)

class UserCoursesView(generics.ListAPIView):
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.user_type == User.Types.INSTRUCTOR:
            return Course.objects.filter(instructor=self.request.user)
        else:
            return Course.objects.filter(enrollments__student=self.request.user)

class CourseSearchView(generics.ListAPIView):
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Course.objects.filter(is_published=True)
        search_term = self.request.query_params.get('q')
        category = self.request.query_params.get('category')
        level = self.request.query_params.get('level')
        language = self.request.query_params.get('language')

        if search_term:
            queryset = queryset.filter(
                Q(title__icontains=search_term) |
                Q(description__icontains=search_term)
            )
        
        if category:
            queryset = queryset.filter(category_id=category)
        
        if level:
            queryset = queryset.filter(level=level)
        
        if language:
            queryset = queryset.filter(language=language)
        
        return queryset

class CourseDetailView(generics.RetrieveAPIView):
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated]
    queryset = Course.objects.all()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


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

# Health check endpoint
@api_view(['GET'])
def health_check(request):
    """
    Simple health check endpoint
    """
    return Response({
        'status': 'healthy',
        'timestamp': timezone.now().isoformat(),
        'version': '1.0.0'
    }, status=status.HTTP_200_OK)

# Additional admin views you might need

@api_view(['GET'])
@permission_classes([IsAdminUser])
def course_analytics(request):
    """
    Get course analytics data
    """
    try:
        courses_with_stats = Course.objects.annotate(
            enrollment_count=Count('enrollments'),
            avg_rating=Avg('reviews__rating')
        ).select_related('instructor', 'category')
        
        analytics_data = []
        for course in courses_with_stats:
            analytics_data.append({
                'id': course.id,
                'title': course.title,
                'instructor': course.instructor.get_full_name() or course.instructor.username,
                'category': course.category.name if course.category else None,
                'enrollmentCount': course.enrollment_count,
                'averageRating': float(course.avg_rating) if course.avg_rating else 0,
                'reviewCount': course.reviews.count(),
                'isPublished': course.is_published,
                'createdAt': course.created_at.isoformat()
            })
        
        return Response(analytics_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'Failed to fetch course analytics: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAdminUser])
def user_analytics(request):
    """
    Get user analytics data
    """
    try:
        # User registration trends (last 30 days)
        thirty_days_ago = timezone.now() - timedelta(days=30)
        recent_users = User.objects.filter(date_joined__gte=thirty_days_ago)
        
        # User type distribution
        user_type_counts = User.objects.values('user_type').annotate(count=Count('id'))
        
        # Active users (users who have enrolled in courses)
        active_users = User.objects.filter(enrollments__isnull=False).distinct().count()
        
        analytics_data = {
            'totalUsers': User.objects.count(),
            'recentUsers': recent_users.count(),
            'activeUsers': active_users,
            'userTypeDistribution': list(user_type_counts),
            'registrationTrend': [
                {
                    'date': (timezone.now() - timedelta(days=i)).date().isoformat(),
                    'count': User.objects.filter(
                        date_joined__date=timezone.now().date() - timedelta(days=i)
                    ).count()
                }
                for i in range(7)
            ]
        }
        
        return Response(analytics_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'Failed to fetch user analytics: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
@api_view(['GET'])
@permission_classes([IsAdminUser])
def recent_enrollments(request):
    """
    Get recent enrollments for admin dashboard
    """
    try:
        limit = int(request.query_params.get('limit', 10))
        
        # Get recent enrollments with related data
        recent_enrollments = Enrollment.objects.select_related(
            'student', 'course', 'course__instructor'
        ).order_by('-enrolled_at')[:limit]
        
        # Serialize the data
        enrollments_data = []
        for enrollment in recent_enrollments:
            enrollments_data.append({
                'id': str(enrollment.id),  # Convert UUID to string
                'studentId': str(enrollment.student.id),
                'courseId': str(enrollment.course.id),
                'enrolledAt': enrollment.enrolled_at.isoformat(),
                'completed': enrollment.completed,
                'progressPercentage': enrollment.progress_percentage,
                'student': {
                    'id': str(enrollment.student.id),
                    'name': enrollment.student.get_full_name() or enrollment.student.username,
                    'email': enrollment.student.email,
                    'userType': enrollment.student.user_type
                },
                'course': {
                    'id': str(enrollment.course.id),
                    'title': enrollment.course.title,
                    'instructor': enrollment.course.instructor.get_full_name() or enrollment.course.instructor.username,
                    'price': float(enrollment.course.price) if enrollment.course.price else 0,
                    'level': enrollment.course.level,
                    'isPublished': enrollment.course.is_published
                }
            })
        
        return Response({
            'enrollments': enrollments_data,
            'total': Enrollment.objects.count(),
            'limit': limit
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'Failed to fetch recent enrollments: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
class CourseCategoryViewSet(viewsets.ModelViewSet):
    queryset = CourseCategory.objects.all()
    serializer_class = CourseCategorySerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminUser()]
        return super().get_permissions()

class QaItemViewSet(viewsets.ModelViewSet):
    serializer_class = QaItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        lecture_id = self.request.query_params.get('lecture_id')
        if lecture_id:
            return QaItem.objects.filter(lecture_id=lecture_id)
        return QaItem.objects.filter(asked_by=self.request.user)

    def perform_create(self, serializer):
        serializer.save(asked_by=self.request.user)

    @action(detail=True, methods=['post'])
    def answer(self, request, pk=None):
        qa = self.get_object()
        answer = request.data.get('answer')
        if not answer:
            return Response({'detail': 'Answer is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        qa.answer = answer
        qa.save()
        return Response({'detail': 'Answer submitted successfully'}, status=status.HTTP_200_OK)

class ProjectToolViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectToolSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        lecture_id = self.request.query_params.get('lecture_id')
        if lecture_id:
            return ProjectTool.objects.filter(lecture_id=lecture_id)
        return ProjectTool.objects.none()

class QuizQuestionViewSet(viewsets.ModelViewSet):
    serializer_class = QuizQuestionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        quiz_id = self.request.query_params.get('quiz_id')
        if quiz_id:
            return QuizQuestion.objects.filter(quiz_id=quiz_id)
        return QuizQuestion.objects.none()

    def perform_create(self, serializer):
        quiz_id = self.request.data.get('quiz_id')
        if not quiz_id:
            return Response({'detail': 'quiz_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()

class QuizTaskViewSet(viewsets.ModelViewSet):
    serializer_class = QuizTaskSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        quiz_id = self.request.query_params.get('quiz_id')
        if quiz_id:
            return QuizTask.objects.filter(quiz_id=quiz_id)
        return QuizTask.objects.none()

class GradingCriterionViewSet(viewsets.ModelViewSet):
    serializer_class = GradingCriterionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        task_id = self.request.query_params.get('task_id')
        if task_id:
            return GradingCriterion.objects.filter(task_id=task_id)
        return GradingCriterion.objects.none()

class SubmissionFileViewSet(viewsets.ModelViewSet):
    serializer_class = SubmissionFileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        submission_id = self.request.query_params.get('submission_id')
        if submission_id:
            return SubmissionFile.objects.filter(submission_id=submission_id)
        return SubmissionFile.objects.filter(submission__student=self.request.user)

class TaskGradeViewSet(viewsets.ModelViewSet):
    serializer_class = TaskGradeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        grade_id = self.request.query_params.get('grade_id')
        if grade_id:
            return TaskGrade.objects.filter(grade_id=grade_id)
        return TaskGrade.objects.filter(grade__student=self.request.user)

class CriteriaGradeViewSet(viewsets.ModelViewSet):
    serializer_class = CriteriaGradeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        task_grade_id = self.request.query_params.get('task_grade_id')
        if task_grade_id:
            return CriteriaGrade.objects.filter(task_grade_id=task_grade_id)
        return CriteriaGrade.objects.filter(task_grade__grade__student=self.request.user)

class FaqViewSet(viewsets.ModelViewSet):
    serializer_class = FaqSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        course_id = self.request.query_params.get('course_id')
        if course_id:
            return Faq.objects.filter(course_id=course_id)
        return Faq.objects.none()

class AnnouncementViewSet(viewsets.ModelViewSet):
    serializer_class = AnnouncementSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        course_id = self.request.query_params.get('course_id')
        if course_id:
            return Announcement.objects.filter(course_id=course_id)
        return Announcement.objects.none()

class CalendarNotificationViewSet(viewsets.ModelViewSet):
    serializer_class = CalendarNotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return CalendarNotification.objects.filter(user=self.request.user)

class NotificationPreferencesViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationPreferencesSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return NotificationPreferences.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class CalendarPermissionsViewSet(viewsets.ModelViewSet):
    serializer_class = CalendarPermissionsSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return CalendarPermissions.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class PlannedCourseReleaseViewSet(viewsets.ModelViewSet):
    serializer_class = PlannedCourseReleaseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return PlannedCourseRelease.objects.filter(student=self.request.user)

class DripScheduleViewSet(viewsets.ModelViewSet):
    serializer_class = DripScheduleSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        course_id = self.request.query_params.get('course_id')
        if course_id:
            return DripSchedule.objects.filter(course_id=course_id)
        return DripSchedule.objects.all()

class DripScheduleEntryViewSet(viewsets.ModelViewSet):
    serializer_class = DripScheduleEntrySerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        schedule_id = self.request.query_params.get('schedule_id')
        if schedule_id:
            return DripScheduleEntry.objects.filter(schedule_id=schedule_id)
        return DripScheduleEntry.objects.all()