# views.py
from rest_framework import viewsets, generics, status, permissions, serializers
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from django.db.models import Q, Prefetch, F
from django.db import transaction, OperationalError, IntegrityError
from django.shortcuts import get_object_or_404
import time
from django.db import models
from django.core.exceptions import PermissionDenied

from authentication.serializers import UserSerializer  # Add this import

from .models import (
    Course, CourseCategory, CourseSection, Lecture, LectureResource,
    QaItem, ProjectTool, Quiz, QuizQuestion, QuizTask
)
from .serializers import (
    CourseDetailSerializer, CourseSerializer, CourseCategorySerializer, CourseSectionSerializer,
    LectureSerializer, LectureResourceSerializer, LectureCreateSerializer,
    AdminCourseSerializer, QaItemSerializer, ProjectToolSerializer,
    QuizSerializer, QuizQuestionSerializer, QuizTaskSerializer
)
from core.views import BaseModelViewSet
from core.utils import success_response, error_response
from core.permissions import IsAdminUser, IsInstructor, IsAdminOrCourseInstructor, CanAccessCourseContent
from authentication.models import User


def execute_with_retry(func, max_retries=3, initial_delay=0.1):
    """
    Helper function to execute database operations with retry logic
    for handling temporary database locks or conflicts.
    """
    retry_count = 0
    delay = initial_delay
    
    while retry_count < max_retries:
        try:
            return func()
        except OperationalError as e:
            if 'database is locked' in str(e):
                retry_count += 1
                if retry_count >= max_retries:
                    raise
                time.sleep(delay)
                delay *= 2  # exponential backoff
            else:
                raise
        except IntegrityError as e:
            raise serializers.ValidationError(f"Database integrity error: {str(e)}")
        except Exception as e:
            raise serializers.ValidationError(f"An error occurred: {str(e)}")


class CourseFilterMixin:
    """Mixin for common course filtering logic."""
    def filter_queryset(self, queryset):
        queryset = super().get_queryset()
        
        # Status filter
        status_filter = self.request.query_params.get('status')
        if status_filter == 'published':
            queryset = queryset.filter(is_published=True)
        elif status_filter == 'draft':
            queryset = queryset.filter(is_published=False)
        elif status_filter == 'archived':
            queryset = queryset.filter(is_active=False)
        
        # Search filter
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | 
                Q(description__icontains=search) |
                Q(instructor__first_name__icontains=search) |
                Q(instructor__last_name__icontains=search)
            )
        
        return queryset


class CourseViewSet(BaseModelViewSet, CourseFilterMixin):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer

    def get_permissions(self):
        # Allow public access for list and retrieve actions
        if self.action in ['list', 'retrieve']:
            return []
        elif self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsAdminOrCourseInstructor()]
        elif self.action in ['enroll', 'update_status', 'reorder_sections']:
            return [IsAuthenticated()]
        return [IsAuthenticated()]

    def get_queryset(self):
        queryset = super().filter_queryset(super().get_queryset())
        
        # For public access (non-authenticated users), only show published courses
        if not self.request.user.is_authenticated:
            return queryset.filter(is_published=True, is_active=True)
        
        # Admin users can see all courses, regular authenticated users only see published ones
        if not (self.request.user.is_staff or self.request.user.is_superuser):
            queryset = queryset.filter(is_published=True)
        return queryset

    def create(self, request, *args, **kwargs):
        print("\n=== INCOMING REQUEST ===")
        print(f"Content-Type: {request.content_type}")
        print(f"Data keys: {list(request.data.keys())}")
        print(f"Files keys: {list(request.FILES.keys())}")
        print(f"User: {request.user}")
        
        # Debug: Check for category_id in both data and POST
        print(f"category_id in data: {request.data.get('category_id')}")
        print(f"category_id in POST: {request.POST.get('category_id')}")
        print("=======================\n")

        # Manually verify category_id exists
        if 'category_id' not in request.data and 'category_id' not in request.POST:
            return Response(
                {"category_id": ["This field is required."]},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Add serializer validation debugging
        serializer = self.get_serializer(data=request.data)
        print(f"Serializer is_valid: {serializer.is_valid()}")
        if not serializer.is_valid():
            print(f"Serializer errors: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Don't call super().create() - do it manually for better debugging
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        except Exception as e:
            print(f"Exception during creation: {str(e)}")
            print(f"Exception type: {type(e)}")
            import traceback
            traceback.print_exc()
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def perform_create(self, serializer):
        print("\n=== PERFORM CREATE START ===")
        print("Initial data:", serializer.initial_data)
        print("Request data:", self.request.data)
        print("Validated data:", serializer.validated_data)
        
        def _perform_create():
            try:
                # Get instructor_id from request data
                instructor_id = self.request.data.get('instructor_id')
                print(f"Instructor ID from request: {instructor_id}")
                
                if instructor_id:
                    # Admin or staff can assign any instructor
                    if self.request.user.is_staff or self.request.user.is_superuser:
                        try:
                            instructor = User.objects.get(id=instructor_id)
                            print(f"Found instructor: {instructor}")
                            serializer.save(instructor=instructor)
                        except User.DoesNotExist:
                            print(f"Instructor with ID {instructor_id} not found, using current user")
                            serializer.save(instructor=self.request.user)
                    else:
                        # Regular users can only create courses for themselves
                        print("Regular user, using current user as instructor")
                        serializer.save(instructor=self.request.user)
                else:
                    # No instructor_id provided, default to current user
                    print("No instructor_id provided, using current user")
                    serializer.save(instructor=self.request.user)
                
                print("=== PERFORM CREATE SUCCESS ===")
                print(f"Created course: {serializer.instance}")
                print("==============================\n")
                
            except Exception as e:
                print(f"Error in _perform_create: {str(e)}")
                print(f"Error type: {type(e)}")
                import traceback
                traceback.print_exc()
                raise
        
        return execute_with_retry(_perform_create)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def enroll(self, request, pk=None):
        def _enroll():
            course = self.get_object()
            from enrollments.models import Enrollment
            
            if Enrollment.objects.filter(student=request.user, course=course).exists():
                return error_response('Already enrolled', status_code=status.HTTP_400_BAD_REQUEST)
            
            with transaction.atomic():
                enrollment = Enrollment.objects.create(
                    student=request.user,
                    course=course
                )
                CourseProgress.objects.create(enrollment=enrollment)
                return success_response('Enrolled successfully', status_code=status.HTTP_201_CREATED)
        
        return execute_with_retry(_enroll)

    @action(detail=True, methods=['patch'], permission_classes=[IsAuthenticated])
    def update_status(self, request, pk=None):
        """Update course publication status"""
        def _update_status():
            course = self.get_object()
            
            # Admin users or course instructor can update status
            if not (request.user.is_staff or request.user.is_superuser or course.instructor == request.user):
                return error_response('Permission denied', status_code=status.HTTP_403_FORBIDDEN)
            
            is_published = request.data.get('is_published')
            if is_published is None:
                return error_response('is_published field is required', status_code=status.HTTP_400_BAD_REQUEST)
            
            with transaction.atomic():
                course.is_published = is_published
                course.save()
                return success_response('Course status updated successfully')
        
        return execute_with_retry(_update_status)
    
    @action(detail=True, methods=['patch'], url_path='archive', permission_classes=[IsAuthenticated])
    def archive(self, request, pk=None):
        """Toggle course archive status"""
        def _archive():
            course = self.get_object()
            is_active = request.data.get('is_active', True)
            
            with transaction.atomic():
                # Update the course
                course.is_active = is_active
                course.save()
                
                # Serialize and return updated course
                serializer = self.get_serializer(course)
                return Response(serializer.data)
        
        return execute_with_retry(_archive)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def reorder_sections(self, request, pk=None):
        """Reorder sections within a course"""
        def _reorder_sections():
            course = self.get_object()
            
            # Check permissions
            if not (request.user.is_staff or request.user.is_superuser or course.instructor == request.user):
                return error_response('Permission denied', status_code=status.HTTP_403_FORBIDDEN)
            
            sections_data = request.data.get('sections', [])
            
            if not sections_data:
                return error_response('sections data is required', status_code=status.HTTP_400_BAD_REQUEST)
            
            try:
                with transaction.atomic():
                    # Lock all sections for this course to prevent concurrent modifications
                    sections = CourseSection.objects.filter(course=course).select_for_update()
                    
                    for section_data in sections_data:
                        section = sections.get(id=section_data['id'])
                        section.order = section_data['order']
                        section.save()
                
                return success_response('Sections reordered successfully', status_code=status.HTTP_200_OK)
            except CourseSection.DoesNotExist:
                return error_response('One or more sections not found', status_code=status.HTTP_404_NOT_FOUND)
            except Exception as e:
                return error_response(str(e), status_code=status.HTTP_400_BAD_REQUEST)
        
        return execute_with_retry(_reorder_sections)

    @action(detail=True, methods=['get'])
    def sections(self, request, pk=None):
        """Get sections for a specific course with optimized queries and complete lecture data"""
        def _get_sections():
            course = self.get_object()
            
            # For non-authenticated users, only show published courses
            if not request.user.is_authenticated and not course.is_published:
                from django.http import Http404
                raise Http404("Course not found")
            
            # Enhanced prefetch to include all lecture data and related content
            sections = course.sections.prefetch_related(
                Prefetch(
                    'lectures',
                    queryset=Lecture.objects.order_by('order').prefetch_related(
                        # Include all lecture resources
                        Prefetch('resources', queryset=LectureResource.objects.all()),
                        # Include all Q&A items with user details
                        Prefetch('qa_items', queryset=QaItem.objects.select_related('asked_by')),
                        # Include all project tools
                        Prefetch('project_tools', queryset=ProjectTool.objects.all()),
                        # Include all quizzes with questions and tasks
                        Prefetch('quizzes', queryset=Quiz.objects.prefetch_related(
                            Prefetch('questions', queryset=QuizQuestion.objects.order_by('order')),
                            Prefetch('tasks', queryset=QuizTask.objects.order_by('order'))
                        ))
                    )
                ),
                # Include section-level quizzes
                Prefetch('quizzes', queryset=Quiz.objects.prefetch_related(
                    Prefetch('questions', queryset=QuizQuestion.objects.order_by('order')),
                    Prefetch('tasks', queryset=QuizTask.objects.order_by('order'))
                ))
            ).order_by('order')
            
            sections_data = []
            for section in sections:
                lectures_data = []
                
                for lecture in section.lectures.all():
                    # Build complete lecture data
                    lecture_data = {
                        'id': lecture.id,
                        'title': lecture.title,
                        'order': lecture.order,
                        'duration': lecture.duration,
                        'overview': lecture.overview,
                        'video_url': lecture.video_url,
                        'preview_available': lecture.preview_available,
                        'created_at': lecture.created_at,
                        'updated_at': lecture.updated_at,
                        
                        # Format duration for display
                        'duration_formatted': self._format_duration(lecture.duration),
                        
                        # Include all lecture resources
                        'resources': [{
                            'id': resource.id,
                            'title': resource.title,
                            'description': resource.description,
                            'resource_type': resource.resource_type,
                            'kind': resource.kind,
                            'url': resource.url,
                            'file_url': resource.file_url,
                            'external_url': resource.external_url,
                            'provider': resource.provider,
                            'duration_seconds': resource.duration_seconds,
                            'is_downloadable': resource.is_downloadable,
                            'file_size': resource.file_size,
                            'mime_type': resource.mime_type,
                            'effective_url': resource.effective_url,
                            'created_at': resource.created_at,
                            'updated_at': resource.updated_at
                        } for resource in lecture.resources.all()],
                        
                        # Include all Q&A items
                        'qa_items': [{
                            'id': qa.id,
                            'question': qa.question,
                            'answer': qa.answer,
                            'upvotes': qa.upvotes,
                            'resolved': qa.resolved,
                            'created_at': qa.created_at,
                            'updated_at': qa.updated_at,
                            'asked_by': {
                                'id': qa.asked_by.id,
                                'first_name': qa.asked_by.first_name,
                                'last_name': qa.asked_by.last_name,
                                'email': qa.asked_by.email if request.user.is_authenticated else None
                            } if qa.asked_by else None
                        } for qa in lecture.qa_items.all()],
                        
                        # Include all project tools
                        'project_tools': [{
                            'id': tool.id,
                            'name': tool.name,
                            'description': tool.description,
                            'url': tool.url,
                            'icon': tool.icon,
                            'created_at': tool.created_at,
                            'updated_at': tool.updated_at
                        } for tool in lecture.project_tools.all()],
                        
                        # Include all quizzes with questions and tasks
                        'quizzes': [{
                            'id': quiz.id,
                            'title': quiz.title,
                            'description': quiz.description,
                            'instructions': quiz.instructions,
                            'points_possible': quiz.points_possible,
                            'due_date': quiz.due_date,
                            'is_published': quiz.is_published,
                            'allow_multiple_attempts': quiz.allow_multiple_attempts,
                            'max_attempts': quiz.max_attempts,
                            'time_limit_minutes': quiz.time_limit_minutes,
                            'created_at': quiz.created_at,
                            'updated_at': quiz.updated_at,
                            
                            # Include quiz questions
                            'questions': [{
                                'id': question.id,
                                'question': question.question,
                                'question_type': question.question_type,
                                'options': question.options,
                                'correct_option_index': question.correct_option_index if request.user.is_authenticated else None,
                                'correct_answer': question.correct_answer if request.user.is_authenticated else None,
                                'points': question.points,
                                'explanation': question.explanation,
                                'order': question.order,
                                'created_at': question.created_at,
                                'updated_at': question.updated_at
                            } for question in quiz.questions.all()],
                            
                            # Include quiz tasks
                            'tasks': [{
                                'id': task.id,
                                'title': task.title,
                                'description': task.description,
                                'points': task.points,
                                'accepts_files': task.accepts_files,
                                'accepts_text': task.accepts_text,
                                'accepted_file_types': task.accepted_file_types,
                                'max_file_size': task.max_file_size,
                                'max_files': task.max_files,
                                'sample_answer': task.sample_answer,
                                'required': task.required,
                                'order': task.order,
                                'created_at': task.created_at,
                                'updated_at': task.updated_at
                            } for task in quiz.tasks.all()]
                        } for quiz in lecture.quizzes.all()],
                        
                        # Add content statistics
                        'content_stats': {
                            'resources_count': lecture.resources.count(),
                            'qa_items_count': lecture.qa_items.count(),
                            'project_tools_count': lecture.project_tools.count(),
                            'quizzes_count': lecture.quizzes.count(),
                            'total_quiz_questions': sum(quiz.questions.count() for quiz in lecture.quizzes.all()),
                            'total_quiz_tasks': sum(quiz.tasks.count() for quiz in lecture.quizzes.all())
                        },
                        
                        # Convenience flags
                        'has_resources': lecture.resources.exists(),
                        'has_qa_items': lecture.qa_items.exists(),
                        'has_project_tools': lecture.project_tools.exists(),
                        'has_quiz': lecture.quizzes.exists(),
                        'has_video': bool(lecture.video_url),
                        'is_completed': False  # This would need to be calculated based on user progress
                    }
                    
                    lectures_data.append(lecture_data)
                
                # Build section data
                section_data = {
                    'id': section.id,
                    'title': section.title,
                    'description': section.description,
                    'order': section.order,
                    'created_at': section.created_at,
                    'updated_at': section.updated_at,
                    'lectures': lectures_data,
                    
                    # Include section-level quizzes
                    'quizzes': [{
                        'id': quiz.id,
                        'title': quiz.title,
                        'description': quiz.description,
                        'instructions': quiz.instructions,
                        'points_possible': quiz.points_possible,
                        'due_date': quiz.due_date,
                        'is_published': quiz.is_published,
                        'allow_multiple_attempts': quiz.allow_multiple_attempts,
                        'max_attempts': quiz.max_attempts,
                        'time_limit_minutes': quiz.time_limit_minutes,
                        'created_at': quiz.created_at,
                        'updated_at': quiz.updated_at,
                        
                        # Include quiz questions
                        'questions': [{
                            'id': question.id,
                            'question': question.question,
                            'question_type': question.question_type,
                            'options': question.options,
                            'correct_option_index': question.correct_option_index if request.user.is_authenticated else None,
                            'correct_answer': question.correct_answer if request.user.is_authenticated else None,
                            'points': question.points,
                            'explanation': question.explanation,
                            'order': question.order,
                            'created_at': question.created_at,
                            'updated_at': question.updated_at
                        } for question in quiz.questions.all()],
                        
                        # Include quiz tasks
                        'tasks': [{
                            'id': task.id,
                            'title': task.title,
                            'description': task.description,
                            'points': task.points,
                            'accepts_files': task.accepts_files,
                            'accepts_text': task.accepts_text,
                            'accepted_file_types': task.accepted_file_types,
                            'max_file_size': task.max_file_size,
                            'max_files': task.max_files,
                            'sample_answer': task.sample_answer,
                            'required': task.required,
                            'order': task.order,
                            'created_at': task.created_at,
                            'updated_at': task.updated_at
                        } for task in quiz.tasks.all()]
                    } for quiz in section.quizzes.all()],
                    
                    # Add section-level statistics
                    'section_stats': {
                        'lectures_count': len(lectures_data),
                        'total_resources': sum(lecture['content_stats']['resources_count'] for lecture in lectures_data),
                        'total_qa_items': sum(lecture['content_stats']['qa_items_count'] for lecture in lectures_data),
                        'total_project_tools': sum(lecture['content_stats']['project_tools_count'] for lecture in lectures_data),
                        'total_lecture_quizzes': sum(lecture['content_stats']['quizzes_count'] for lecture in lectures_data),
                        'section_quizzes_count': section.quizzes.count(),
                        'total_duration': sum(self._parse_duration_to_minutes(lecture['duration']) for lecture in lectures_data)
                    },
                    
                    # Convenience flags
                    'has_lectures': len(lectures_data) > 0,
                    'has_quizzes': section.quizzes.exists()
                }
                
                sections_data.append(section_data)
            
            # Calculate course-level statistics
            course_stats = {
                'total_sections': len(sections_data),
                'total_lectures': sum(section['section_stats']['lectures_count'] for section in sections_data),
                'total_resources': sum(section['section_stats']['total_resources'] for section in sections_data),
                'total_qa_items': sum(section['section_stats']['total_qa_items'] for section in sections_data),
                'total_project_tools': sum(section['section_stats']['total_project_tools'] for section in sections_data),
                'total_lecture_quizzes': sum(section['section_stats']['total_lecture_quizzes'] for section in sections_data),
                'total_section_quizzes': sum(section['section_stats']['section_quizzes_count'] for section in sections_data),
                'total_duration_minutes': sum(section['section_stats']['total_duration'] for section in sections_data)
            }
            
            # Calculate total quizzes including course-level quizzes
            course_level_quizzes = Quiz.objects.filter(course=course, section__isnull=True, lecture__isnull=True).count()
            course_stats['total_course_quizzes'] = course_level_quizzes
            course_stats['total_quizzes'] = (
                course_stats['total_lecture_quizzes'] + 
                course_stats['total_section_quizzes'] + 
                course_stats['total_course_quizzes']
            )
            
            # Format total duration
            total_minutes = course_stats['total_duration_minutes']
            hours = total_minutes // 60
            minutes = total_minutes % 60
            course_stats['total_duration_formatted'] = f"{hours}h {minutes}min" if hours > 0 else f"{minutes}min"
            
            return Response({
                'results': sections_data,
                'course_stats': course_stats,
                'course_info': {
                    'id': course.id,
                    'title': course.title,
                    'slug': course.slug,
                    'description': course.description,
                    'is_published': course.is_published,
                    'is_active': course.is_active
                }
            })
        
        return execute_with_retry(_get_sections)
    
    def _format_duration(self, duration_str):
        """Format duration string for display"""
        if not duration_str:
            return "0 min"
        
        try:
            # Parse duration string (assuming format like "01:30:45" or "00:30:00")
            parts = duration_str.split(':')
            if len(parts) == 3:
                hours, minutes, seconds = map(int, parts)
                total_minutes = hours * 60 + minutes
                if seconds >= 30:  # Round up if seconds >= 30
                    total_minutes += 1
                
                if total_minutes >= 60:
                    hours = total_minutes // 60
                    minutes = total_minutes % 60
                    return f"{hours}h {minutes}min" if minutes > 0 else f"{hours}h"
                else:
                    return f"{total_minutes} min"
            else:
                return duration_str
        except (ValueError, AttributeError):
            return duration_str or "0 min"
    
    def _parse_duration_to_minutes(self, duration_str):
        """Parse duration string to total minutes"""
        if not duration_str:
            return 0
        
        try:
            parts = duration_str.split(':')
            if len(parts) == 3:
                hours, minutes, seconds = map(int, parts)
                total_minutes = hours * 60 + minutes
                if seconds >= 30:  # Round up if seconds >= 30
                    total_minutes += 1
                return total_minutes
            else:
                return 0
        except (ValueError, AttributeError):
            return 0
        
class AdminCourseViewSet(BaseModelViewSet, CourseFilterMixin):
    """Admin-specific course management with additional fields and controls"""
    queryset = Course.objects.all()
    serializer_class = AdminCourseSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get_queryset(self):
        def _get_queryset():
            queryset = super().filter_queryset(super().get_queryset())
            
            # Sorting
            sort = self.request.query_params.get('sort', 'newest')
            if sort == 'newest':
                queryset = queryset.order_by('-created_at')
            elif sort == 'oldest':
                queryset = queryset.order_by('created_at')
            elif sort == 'popular':
                queryset = queryset.order_by('-students_enrolled')
            
            return queryset
        
        return execute_with_retry(_get_queryset)


class CourseCategoryViewSet(BaseModelViewSet):
    queryset = CourseCategory.objects.all()
    serializer_class = CourseCategorySerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsAdminUser()]
        return [IsAuthenticated()]



class CourseSearchView(generics.ListAPIView):
    serializer_class = CourseSerializer
    permission_classes = []  # Allow public access
    pagination_class = None  # Disable pagination for search results

    def get_queryset(self):
        def _get_queryset():
            # Only show published and active courses for public search
            queryset = Course.objects.filter(is_published=True, is_active=True)
            search_term = self.request.query_params.get('q')
            category = self.request.query_params.get('category')
            level = self.request.query_params.get('level')
            language = self.request.query_params.get('language')

            if search_term:
                queryset = queryset.filter(
                    Q(title__icontains=search_term) |
                    Q(description__icontains=search_term) |
                    Q(instructor__first_name__icontains=search_term) |
                    Q(instructor__last_name__icontains=search_term)
                )
            
            if category:
                queryset = queryset.filter(category_id=category)
            if level:
                queryset = queryset.filter(level=level)
            if language:
                queryset = queryset.filter(language=language)
            
            return queryset
        
        return execute_with_retry(_get_queryset)


class CourseDetailView(generics.RetrieveAPIView):
    """
    Comprehensive course detail endpoint that returns ALL data needed for the course detail page.
    This includes:
    - Course basic info and metadata
    - Instructor details
    - All sections with their lectures
    - All lecture resources, Q&A items, project tools
    - All quizzes with their questions and tasks
    - User enrollment and progress data
    - Course statistics and summaries
    """
    serializer_class = CourseDetailSerializer
    permission_classes = []  # Allow public access
    lookup_field = 'slug'  # Use slug for SEO-friendly URLs
    lookup_url_kwarg = 'slug'
    
    def get_queryset(self):
        queryset = Course.objects.select_related(
            'instructor',
            'category'
        ).prefetch_related(
            Prefetch(
                'sections',
                queryset=CourseSection.objects.order_by('order').prefetch_related(
                    Prefetch(
                        'lectures',
                        queryset=Lecture.objects.order_by('order').prefetch_related(
                            Prefetch('resources'),
                            Prefetch('qa_items', queryset=QaItem.objects.select_related('asked_by')),
                            Prefetch('project_tools'),
                            Prefetch('quizzes', queryset=Quiz.objects.prefetch_related(
                                Prefetch('questions', queryset=QuizQuestion.objects.order_by('order')),
                                Prefetch('tasks', queryset=QuizTask.objects.order_by('order'))
                            )
                        )
                    ),
                    )
                )
            ),
            Prefetch('quizzes', queryset=Quiz.objects.prefetch_related(
                Prefetch('questions', queryset=QuizQuestion.objects.order_by('order')),
                Prefetch('tasks', queryset=QuizTask.objects.order_by('order'))
            ))
        )
        
        # Filter based on user authentication and permissions
        if not self.request.user.is_authenticated:
            # Non-authenticated users can only see published and active courses
            return queryset.filter(is_published=True, is_active=True)
        
        # Authenticated non-admin users can only see published courses
        if not (self.request.user.is_staff or self.request.user.is_superuser):
            return queryset.filter(is_published=True)
        
        # Admin users can see all courses
        return queryset

    def get_serializer_context(self):
        """Add request context for user-specific data like enrollment status"""
        context = super().get_serializer_context()
        context['request'] = self.request
        context['include_full_details'] = True
        return context
    
    def retrieve(self, request, *args, **kwargs):
        """
        Override retrieve to add additional course statistics and data
        that might be expensive to compute in serializers.
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        
        # Add any additional real-time data if needed
        data = serializer.data
        
        # Add comprehensive stats if not already included in serializer
        if 'stats' not in data:
            # Calculate comprehensive stats
            stats = instance.sections.aggregate(
                total_sections=models.Count('id'),
                total_lectures=models.Count('lectures'),
                total_duration=models.Sum('lectures__duration'),
                total_resources=models.Count('lectures__resources'),
                total_qa_items=models.Count('lectures__qa_items'),
                total_project_tools=models.Count('lectures__project_tools'),
                total_lecture_quizzes=models.Count('lectures__quizzes')  # FIXED: quiz -> quizzes
            )
            
            # Add section-level and course-level quiz counts
            section_quizzes = instance.sections.filter(quizzes__isnull=False).count()  # FIXED: quiz -> quizzes
            course_quizzes = Quiz.objects.filter(course=instance, section__isnull=True, lecture__isnull=True).count()
            total_quizzes = (stats['total_lecture_quizzes'] or 0) + section_quizzes + course_quizzes
            
            # Add stats to response
            data['resources_count'] = stats['total_resources'] or 0
            data['qa_items'] = stats['total_qa_items'] or 0
            data['qa_items_count'] = stats['total_qa_items'] or 0
            data['project_tools'] = stats['total_project_tools'] or 0
            data['project_tools_count'] = stats['total_project_tools'] or 0
            data['quiz'] = total_quizzes
            data['quizzes_count'] = total_quizzes
            data['has_quiz'] = total_quizzes > 0
        
        return Response(data)

class CourseContentView(generics.RetrieveAPIView):
    """
    Enhanced endpoint that returns complete course content structure
    including all lecture resources, Q&A items, project tools, and quizzes.
    Useful for course navigation/content management components.
    """
    serializer_class = CourseDetailSerializer
    permission_classes = []
    lookup_field = 'slug'
    lookup_url_kwarg = 'slug'

    def get_queryset(self):
        """Enhanced queryset with complete lecture content"""
        queryset = Course.objects.select_related(
            'instructor',
            'category'
        ).prefetch_related(
            Prefetch(
                'sections',
                queryset=CourseSection.objects.order_by('order').prefetch_related(
                    Prefetch(
                        'lectures',
                        queryset=Lecture.objects.order_by('order').prefetch_related(
                            # Include all lecture resources
                            Prefetch('resources', queryset=LectureResource.objects.all()),
                            # Include all Q&A items with user details
                            Prefetch('qa_items', queryset=QaItem.objects.select_related('asked_by')),
                            # Include all project tools
                            Prefetch('project_tools', queryset=ProjectTool.objects.all()),
                            # Include all quizzes with questions and tasks
                            Prefetch('quizzes', queryset=Quiz.objects.prefetch_related(
                                Prefetch('questions', queryset=QuizQuestion.objects.order_by('order')),
                                Prefetch('tasks', queryset=QuizTask.objects.order_by('order'))
                            ))
                        )
                    )
                )
            )
        )
        
        if not self.request.user.is_authenticated:
            return queryset.filter(is_published=True, is_active=True)
        
        if not (self.request.user.is_staff or self.request.user.is_superuser):
            return queryset.filter(is_published=True)
        
        return queryset

    def retrieve(self, request, *args, **kwargs):
        """Return complete course structure with all content"""
        instance = self.get_object()
        
        # Create a comprehensive response
        data = {
            'id': instance.id,
            'title': instance.title,
            'slug': instance.slug,
            'description': instance.description,
            'instructor': {
                'id': instance.instructor.id,
                'first_name': instance.instructor.first_name,
                'last_name': instance.instructor.last_name,
                'email': instance.instructor.email if request.user.is_authenticated else None
            },
            'category': {
                'id': instance.category.id,
                'name': instance.category.name
            } if instance.category else None,
            'sections': []
        }
        
        for section in instance.sections.all():
            section_data = {
                'id': section.id,
                'title': section.title,
                'order': section.order,
                'lectures': []
            }
            
            for lecture in section.lectures.all():
                lecture_data = {
                    'id': lecture.id,
                    'title': lecture.title,
                    'overview': lecture.overview,
                    'video_url': lecture.video_url,
                    'duration': lecture.duration,
                    'order': lecture.order,
                    'preview_available': lecture.preview_available,
                    'is_completed': False,  # Calculate based on user progress if needed
                    
                    # Include all lecture resources
                    'resources': [{
                        'id': resource.id,
                        'title': resource.title,
                        'resource_type': resource.resource_type,
                        'file_url': resource.file_url,
                        'external_url': resource.external_url,
                        'description': resource.description,
                        'is_downloadable': resource.is_downloadable,
                        'file_size': resource.file_size,
                        'created_at': resource.created_at
                    } for resource in lecture.resources.all()],
                    
                    # Include all Q&A items
                    'qa_items': [{
                        'id': qa.id,
                        'question': qa.question,
                        'answer': qa.answer,
                        'upvotes': qa.upvotes,
                        'resolved': qa.resolved,
                        'created_at': qa.created_at,
                        'asked_by': {
                            'id': qa.asked_by.id,
                            'first_name': qa.asked_by.first_name,
                            'last_name': qa.asked_by.last_name
                        } if qa.asked_by else None
                    } for qa in lecture.qa_items.all()],
                    
                    # Include all project tools
                    'project_tools': [{
                        'id': tool.id,
                        'name': tool.name,
                        'description': tool.description,
                        'tool_type': tool.tool_type,
                        'url': tool.url,
                        'instructions': tool.instructions,
                        'is_required': tool.is_required,
                        'created_at': tool.created_at
                    } for tool in lecture.project_tools.all()],
                    
                    # Include all quizzes with questions and tasks
                    'quizzes': [{
                        'id': quiz.id,
                        'title': quiz.title,
                        'description': quiz.description,
                        'quiz_type': quiz.quiz_type,
                        'time_limit': quiz.time_limit,
                        'max_attempts': quiz.max_attempts,
                        'passing_score': quiz.passing_score,
                        'is_published': quiz.is_published,
                        'created_at': quiz.created_at,
                        
                        # Include quiz questions
                        'questions': [{
                            'id': question.id,
                            'question_text': question.question_text,
                            'question_type': question.question_type,
                            'options': question.options,
                            'correct_answer': question.correct_answer if request.user.is_authenticated else None,
                            'explanation': question.explanation,
                            'points': question.points,
                            'order': question.order
                        } for question in quiz.questions.all()],
                        
                        # Include quiz tasks
                        'tasks': [{
                            'id': task.id,
                            'title': task.title,
                            'description': task.description,
                            'task_type': task.task_type,
                            'instructions': task.instructions,
                            'expected_output': task.expected_output,
                            'starter_code': task.starter_code,
                            'test_cases': task.test_cases,
                            'points': task.points,
                            'order': task.order
                        } for task in quiz.tasks.all()]
                    } for quiz in lecture.quizzes.all()],
                    
                    # Add content statistics
                    'content_stats': {
                        'resources_count': lecture.resources.count(),
                        'qa_items_count': lecture.qa_items.count(),
                        'project_tools_count': lecture.project_tools.count(),
                        'quizzes_count': lecture.quizzes.count(),
                        'total_quiz_questions': sum(quiz.questions.count() for quiz in lecture.quizzes.all()),
                        'total_quiz_tasks': sum(quiz.tasks.count() for quiz in lecture.quizzes.all())
                    }
                }
                section_data['lectures'].append(lecture_data)
            
            # Add section-level statistics
            section_data['section_stats'] = {
                'lectures_count': len(section_data['lectures']),
                'total_resources': sum(lecture['content_stats']['resources_count'] for lecture in section_data['lectures']),
                'total_qa_items': sum(lecture['content_stats']['qa_items_count'] for lecture in section_data['lectures']),
                'total_project_tools': sum(lecture['content_stats']['project_tools_count'] for lecture in section_data['lectures']),
                'total_quizzes': sum(lecture['content_stats']['quizzes_count'] for lecture in section_data['lectures']),
                'total_duration': sum(lecture['duration'] or 0 for lecture in section_data['lectures'])
            }
            
            data['sections'].append(section_data)
        
        # Add course-level statistics
        data['course_stats'] = {
            'total_sections': len(data['sections']),
            'total_lectures': sum(section['section_stats']['lectures_count'] for section in data['sections']),
            'total_resources': sum(section['section_stats']['total_resources'] for section in data['sections']),
            'total_qa_items': sum(section['section_stats']['total_qa_items'] for section in data['sections']),
            'total_project_tools': sum(section['section_stats']['total_project_tools'] for section in data['sections']),
            'total_quizzes': sum(section['section_stats']['total_quizzes'] for section in data['sections']),
            'total_duration': sum(section['section_stats']['total_duration'] for section in data['sections'])
        }
        
        # Format total duration
        total_minutes = data['course_stats']['total_duration']
        hours = total_minutes // 60
        minutes = total_minutes % 60
        data['course_stats']['total_duration_formatted'] = f"{hours}h {minutes}min" if hours > 0 else f"{minutes}min"
        
        # Add user-specific data if authenticated
        if request.user.is_authenticated:
            try:
                from enrollments.models import Enrollment
                enrollment = Enrollment.objects.get(
                    student=request.user,
                    course=instance
                )
                
                # Add enrollment and progress data
                data['user_data'] = {
                    'is_enrolled': True,
                    'enrollment_date': enrollment.enrollment_date,
                    'progress_percent': enrollment.progress.progress_percent if hasattr(enrollment, 'progress') else 0,
                    'completed_lectures': enrollment.progress.completed_lectures.count() if hasattr(enrollment, 'progress') else 0,
                    'time_spent_minutes': enrollment.progress.time_spent_minutes if hasattr(enrollment, 'progress') else 0,
                    'last_accessed': enrollment.progress.last_accessed if hasattr(enrollment, 'progress') else None
                }
                
                # Mark completed lectures
                if hasattr(enrollment, 'progress'):
                    completed_lecture_ids = set(enrollment.progress.completed_lectures.values_list('id', flat=True))
                    for section in data['sections']:
                        for lecture in section['lectures']:
                            lecture['is_completed'] = lecture['id'] in completed_lecture_ids
                            
            except Enrollment.DoesNotExist:
                data['user_data'] = {
                    'is_enrolled': False
                }
        else:
            data['user_data'] = {
                'is_enrolled': False
            }
        
        return Response(data)


class CourseStatsView(generics.RetrieveAPIView):
    """
    Endpoint that returns comprehensive course statistics.
    Useful for instructor dashboards or analytics.
    """
    permission_classes = []  # Adjust based on your requirements
    lookup_field = 'slug'
    lookup_url_kwarg = 'slug'

    def get_queryset(self):
        return Course.objects.filter(is_published=True, is_active=True)

    def retrieve(self, request, *args, **kwargs):
        """Return comprehensive course statistics"""
        course = self.get_object()
        
        # Aggregate statistics
        stats = course.sections.aggregate(
            total_sections=Count('id'),
            total_lectures=Count('lectures'),
            total_duration=Sum('lectures__duration'),
            total_resources=Count('lectures__resources'),
            total_qa_items=Count('lectures__qa_items'),
            total_quizzes=Count('lectures__quizzes')  # FIXED: quiz -> quizzes
        )
        
        # Add quiz questions and tasks count
        quiz_stats = Quiz.objects.filter(course=course).aggregate(
            total_questions=Count('questions'),
            total_tasks=Count('tasks')
        )
        
        # Combine all stats
        data = {
            'course_id': course.id,
            'course_title': course.title,
            'sections_count': stats['total_sections'] or 0,
            'lectures_count': stats['total_lectures'] or 0,
            'total_duration_minutes': stats['total_duration'] or 0,
            'resources_count': stats['total_resources'] or 0,
            'qa_items_count': stats['total_qa_items'] or 0,
            'quizzes_count': stats['total_quizzes'] or 0,
            'quiz_questions_count': quiz_stats['total_questions'] or 0,
            'quiz_tasks_count': quiz_stats['total_tasks'] or 0,
            'students_enrolled': course.students_enrolled,
            'rating': course.rating,
            'review_count': course.review_count,
        }
        
        # Format duration
        total_minutes = data['total_duration_minutes']
        hours = total_minutes // 60
        minutes = total_minutes % 60
        data['total_duration_formatted'] = f"{hours}h {minutes}min" if hours > 0 else f"{minutes}min"
        
        return Response(data)


class CourseSectionViewSet(BaseModelViewSet):
    """
    ViewSet for managing course sections with protection against duplicate creation.
    Includes proper transaction handling and database-level constraints.
    """
    serializer_class = CourseSectionSerializer
    permission_classes = [IsAdminOrCourseInstructor]
    lookup_field = 'pk'

    def get_queryset(self):
        """Get sections for the specified course, ordered by their position"""
        def _get_queryset():
            course_id = self.kwargs.get('course_pk')
            if not course_id:
                return CourseSection.objects.none()
            return CourseSection.objects.filter(course_id=course_id).order_by('order')
        
        return execute_with_retry(_get_queryset)

    def create(self, request, *args, **kwargs):
        """
        Create a new course section with protection against:
        - Duplicate titles within the same course
        - Order conflicts
        - Race conditions
        """
        def _create():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            course = get_object_or_404(Course, pk=self.kwargs.get('course_pk'))
            
            # Permission check (outside transaction for early failure)
            if not (request.user.is_staff or 
                    request.user.is_superuser or 
                    course.instructor == request.user):
                return error_response(
                    "You don't have permission to create sections for this course",
                    status_code=status.HTTP_403_FORBIDDEN
                )
            
            # Check for duplicate title (case-insensitive)
            title = serializer.validated_data['title']
            if CourseSection.objects.filter(
                course=course, 
                title__iexact=title
            ).exists():
                return error_response(
                    "A section with this title already exists in this course",
                    status_code=status.HTTP_409_CONFLICT
                )

            try:
                with transaction.atomic():
                    # Lock the course sections to prevent concurrent order conflicts
                    sections = CourseSection.objects.filter(
                        course=course
                    ).select_for_update().order_by('-order')
                    
                    last_section = sections.first()
                    next_order = (last_section.order + 1) if last_section else 1
                    
                    # Verify order isn't taken (double-check for race conditions)
                    if CourseSection.objects.filter(
                        course=course, 
                        order=next_order
                    ).exists():
                        raise IntegrityError("Order conflict detected")
                    
                    # Create the section
                    section = serializer.save(
                        course=course, 
                        order=next_order
                    )
                    
                    # Return the created section
                    headers = self.get_success_headers(serializer.data)
                    return Response(
                        serializer.data,
                        status=status.HTTP_201_CREATED,
                        headers=headers
                    )
                    
            except IntegrityError as e:
                return error_response(
                    "Failed to create section due to concurrent modification. Please try again.",
                    status_code=status.HTTP_409_CONFLICT
                )
            except Exception as e:
                return error_response(
                    f"An error occurred: {str(e)}",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
        
        return execute_with_retry(_create)

    def perform_update(self, serializer):
        """Update section with protection against duplicate titles"""
        def _perform_update():
            course = get_object_or_404(Course, pk=self.kwargs.get('course_pk'))
            instance = self.get_object()
            
            # Check for duplicate title (case-insensitive, excluding current instance)
            if 'title' in serializer.validated_data:
                title = serializer.validated_data['title']
                if CourseSection.objects.filter(
                    course=course,
                    title__iexact=title
                ).exclude(pk=instance.pk).exists():
                    raise serializers.ValidationError(
                        "A section with this title already exists in this course"
                    )
            
            with transaction.atomic():
                serializer.save()
        
        return execute_with_retry(_perform_update)

    @action(detail=True, methods=['post'])
    def reorder(self, request, course_pk=None, pk=None):
        """Reorder sections with proper transaction isolation"""
        def _reorder():
            section = self.get_object()
            new_order = request.data.get('order')
            
            if new_order is None or not isinstance(new_order, int):
                return error_response(
                    "Valid order number is required",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                with transaction.atomic():
                    # Lock all sections for this course during reordering
                    sections = CourseSection.objects.filter(
                        course_id=course_pk
                    ).select_for_update().order_by('order')
                    
                    current_order = section.order
                    
                    if new_order < 1:
                        return error_response(
                            "Order must be a positive integer",
                            status_code=status.HTTP_400_BAD_REQUEST
                        )
                    
                    if new_order > sections.count():
                        return error_response(
                            "Order exceeds number of sections",
                            status_code=status.HTTP_400_BAD_REQUEST
                        )
                    
                    if new_order == current_order:
                        return Response({'status': 'no change needed'})
                    
                    # Update orders of affected sections
                    if new_order > current_order:
                        sections.filter(
                            order__gt=current_order,
                            order__lte=new_order
                        ).update(order=models.F('order') - 1)
                    else:
                        sections.filter(
                            order__lt=current_order,
                            order__gte=new_order
                        ).update(order=models.F('order') + 1)
                    
                    section.order = new_order
                    section.save()
                    
                    return Response({'status': 'reorder successful'})
                    
            except Exception as e:
                return error_response(
                    f"Failed to reorder: {str(e)}",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
        
        return execute_with_retry(_reorder)


class LectureViewSet(BaseModelViewSet):
    serializer_class = LectureSerializer
    permission_classes = [IsAuthenticated, CanAccessCourseContent]

    def get_queryset(self):
        def _get_queryset():
            section_id = self.kwargs.get('section_pk')
            return Lecture.objects.filter(section_id=section_id).prefetch_related(
                Prefetch('resources', queryset=LectureResource.objects.all()),
                Prefetch('qa_items', queryset=QaItem.objects.all()),
                Prefetch('project_tools', queryset=ProjectTool.objects.all()),
                Prefetch('quizzes', queryset=Quiz.objects.prefetch_related(
                    Prefetch('questions', queryset=QuizQuestion.objects.all()),
                    Prefetch('tasks', queryset=QuizTask.objects.all())
                ))
            ).order_by('order')
        
        return execute_with_retry(_get_queryset)

    def get_serializer_class(self):
        if self.action == 'create':
            return LectureCreateSerializer
        return super().get_serializer_class()

    def create(self, request, *args, **kwargs):
        """
        Create a new lecture with protection against race conditions and order conflicts.
        """
        def _create():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            section = get_object_or_404(CourseSection, pk=self.kwargs.get('section_pk'))
            
            # Permission check (outside transaction for early failure)
            if not (request.user.is_staff or 
                    request.user.is_superuser or 
                    section.course.instructor == request.user):
                return error_response(
                    "You don't have permission to create lectures for this course",
                    status_code=status.HTTP_403_FORBIDDEN
                )
            
            try:
                with transaction.atomic():
                    # Lock the section's lectures to prevent concurrent order conflicts
                    lectures = Lecture.objects.filter(
                        section=section
                    ).select_for_update().order_by('-order')
                    
                    last_lecture = lectures.first()
                    next_order = (last_lecture.order + 1) if last_lecture else 1
                    
                    # Verify order isn't taken (double-check for race conditions)
                    if Lecture.objects.filter(
                        section=section, 
                        order=next_order
                    ).exists():
                        raise IntegrityError("Order conflict detected")
                    
                    # Create the lecture
                    lecture = serializer.save(
                        section=section, 
                        order=next_order
                    )
                    
                    # Use the main serializer to format the response
                    response_serializer = LectureSerializer(lecture, context={'request': request})
                    
                    headers = self.get_success_headers(response_serializer.data)
                    return Response(
                        response_serializer.data, 
                        status=status.HTTP_201_CREATED, 
                        headers=headers
                    )
                    
            except IntegrityError as e:
                return error_response(
                    "Failed to create lecture due to concurrent modification. Please try again.",
                    status_code=status.HTTP_409_CONFLICT
                )
            except Exception as e:
                return error_response(
                    f"An error occurred: {str(e)}",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
        
        return execute_with_retry(_create)

    def perform_create(self, serializer):
        """
        This method is no longer used since we override create() completely,
        but keeping it for compatibility in case other methods call it.
        """
        def _perform_create():
            section = get_object_or_404(CourseSection, pk=self.kwargs.get('section_pk'))
            # Don't calculate order here - let create() handle it with proper locking
            with transaction.atomic():
                return serializer.save(section=section)
        
        return execute_with_retry(_perform_create)

    @action(detail=True, methods=['post'])
    def reorder(self, request, pk=None, section_pk=None):
        """Reorder lectures with proper transaction isolation"""
        def _reorder():
            lecture = self.get_object()
            new_order = request.data.get('order')
            
            if new_order is None or not isinstance(new_order, int):
                return error_response(
                    "Valid order number is required",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                with transaction.atomic():
                    # Lock all lectures for this section during reordering
                    lectures = Lecture.objects.filter(
                        section_id=section_pk
                    ).select_for_update().order_by('order')
                    
                    current_order = lecture.order
                    
                    if new_order < 1:
                        return error_response(
                            "Order must be a positive integer",
                            status_code=status.HTTP_400_BAD_REQUEST
                        )
                    
                    if new_order > lectures.count():
                        return error_response(
                            "Order exceeds number of lectures",
                            status_code=status.HTTP_400_BAD_REQUEST
                        )
                    
                    if new_order == current_order:
                        return Response({'status': 'no change needed'})
                    
                    # Update orders of affected lectures
                    if new_order > current_order:
                        lectures.filter(
                            order__gt=current_order,
                            order__lte=new_order
                        ).update(order=F('order') - 1)
                    else:
                        lectures.filter(
                            order__lt=current_order,
                            order__gte=new_order
                        ).update(order=F('order') + 1)
                    
                    lecture.order = new_order
                    lecture.save()
                    
                    return Response({'status': 'reorder successful'})
                    
            except Exception as e:
                return error_response(
                    f"Failed to reorder: {str(e)}",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
        
        return execute_with_retry(_reorder)

    @action(detail=True, methods=['post'])
    def add_qa(self, request, pk=None, section_pk=None):
        def _add_qa():
            lecture = self.get_object()
            serializer = QaItemSerializer(data=request.data, context={'request': request})
            if serializer.is_valid():
                with transaction.atomic():
                    serializer.save(lecture=lecture, asked_by=request.user)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        return execute_with_retry(_add_qa)

    @action(detail=True, methods=['post'])
    def add_project_tool(self, request, pk=None, section_pk=None):
        def _add_project_tool():
            lecture = self.get_object()
            serializer = ProjectToolSerializer(data=request.data)
            if serializer.is_valid():
                with transaction.atomic():
                    serializer.save(lecture=lecture)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        return execute_with_retry(_add_project_tool)

    @action(detail=True, methods=['post'])
    def create_quiz(self, request, pk=None, section_pk=None):
        def _create_quiz():
            lecture = self.get_object()
            serializer = QuizSerializer(data=request.data, context={'request': request})
            if serializer.is_valid():
                with transaction.atomic():
                    serializer.save(
                        lecture=lecture,
                        section=lecture.section,
                        course=lecture.section.course
                    )
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        return execute_with_retry(_create_quiz)

    @action(detail=True, methods=['get'])
    def quiz(self, request, pk=None, section_pk=None):
        def _get_quiz():
            lecture = self.get_object()
            quiz = get_object_or_404(Quiz, lecture=lecture)
            serializer = QuizSerializer(quiz, context={'request': request})
            return Response(serializer.data)
        
        return execute_with_retry(_get_quiz)


class LectureResourceViewSet(BaseModelViewSet):
    serializer_class = LectureResourceSerializer
    permission_classes = [IsAuthenticated, CanAccessCourseContent]

    def get_queryset(self):
        def _get_queryset():
            lecture_id = self.kwargs.get('lecture_pk')
            return LectureResource.objects.filter(lecture_id=lecture_id)
        
        return execute_with_retry(_get_queryset)

    def perform_create(self, serializer):
        def _perform_create():
            lecture = get_object_or_404(Lecture, pk=self.kwargs.get('lecture_pk'))
            with transaction.atomic():
                serializer.save(lecture=lecture)
        
        return execute_with_retry(_perform_create)


class QaItemViewSet(BaseModelViewSet):
    serializer_class = QaItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        def _get_queryset():
            lecture_id = self.kwargs.get('lecture_pk')
            return QaItem.objects.filter(lecture_id=lecture_id).select_related('asked_by')
        
        return execute_with_retry(_get_queryset)

    def perform_create(self, serializer):
        def _perform_create():
            lecture = get_object_or_404(Lecture, pk=self.kwargs.get('lecture_pk'))
            with transaction.atomic():
                serializer.save(lecture=lecture, asked_by=self.request.user)
        
        return execute_with_retry(_perform_create)

    @action(detail=True, methods=['post'])
    def upvote(self, request, pk=None, lecture_pk=None):
        def _upvote():
            qa_item = self.get_object()
            with transaction.atomic():
                qa_item.upvotes += 1
                qa_item.save()
            return Response({'upvotes': qa_item.upvotes})
        
        return execute_with_retry(_upvote)

    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None, lecture_pk=None):
        def _resolve():
            qa_item = self.get_object()
            with transaction.atomic():
                qa_item.resolved = True
                qa_item.save()
            return Response({'resolved': qa_item.resolved})
        
        return execute_with_retry(_resolve)


class ProjectToolViewSet(BaseModelViewSet):
    serializer_class = ProjectToolSerializer
    permission_classes = [IsAuthenticated, CanAccessCourseContent]

    def get_queryset(self):
        def _get_queryset():
            lecture_id = self.kwargs.get('lecture_pk')
            return ProjectTool.objects.filter(lecture_id=lecture_id)
        
        return execute_with_retry(_get_queryset)

    def perform_create(self, serializer):
        def _perform_create():
            lecture = get_object_or_404(Lecture, pk=self.kwargs.get('lecture_pk'))
            with transaction.atomic():
                serializer.save(lecture=lecture)
        
        return execute_with_retry(_perform_create)


class QuizViewSet(BaseModelViewSet):
    serializer_class = QuizSerializer
    permission_classes = [IsAuthenticated, CanAccessCourseContent]

    def get_queryset(self):
        def _get_queryset():
            lecture_id = self.kwargs.get('lecture_pk', None)
            section_id = self.kwargs.get('section_pk', None)
            course_id = self.kwargs.get('course_pk', None)
            
            if lecture_id:
                return Quiz.objects.filter(lecture_id=lecture_id).prefetch_related('questions', 'tasks')
            elif section_id:
                return Quiz.objects.filter(section_id=section_id).prefetch_related('questions', 'tasks')
            elif course_id:
                return Quiz.objects.filter(course_id=course_id).prefetch_related('questions', 'tasks')
            return Quiz.objects.none()
        
        return execute_with_retry(_get_queryset)
    
    @action(detail=True, methods=['get'])
    def retrieve_full(self, request, course_pk=None, section_pk=None, lecture_pk=None):
        def _retrieve_full():
            quiz = self.get_object()
            questions = quiz.questions.all()
            tasks = quiz.tasks.all()
            
            return Response({
                'quiz': QuizSerializer(quiz).data,
                'questions': QuizQuestionSerializer(questions, many=True).data,
                'tasks': QuizTaskSerializer(tasks, many=True).data
            })
        
        return execute_with_retry(_retrieve_full)
    
    def get_object(self):
        """Override get_object to handle one-to-one relationship with lecture"""
        def _get_object():
            lecture_id = self.kwargs.get('lecture_pk', None)
            section_id = self.kwargs.get('section_pk', None)
            course_id = self.kwargs.get('course_pk', None)
            
            try:
                if lecture_id:
                    lecture = get_object_or_404(Lecture, pk=lecture_id)
                    return get_object_or_404(Quiz, lecture=lecture)
                elif section_id:
                    section = get_object_or_404(CourseSection, pk=section_id)
                    return get_object_or_404(Quiz, section=section)
                elif course_id:
                    course = get_object_or_404(Course, pk=course_id)
                    return get_object_or_404(Quiz, course=course)
                else:
                    from django.http import Http404
                    raise Http404("Quiz not found")
            except Quiz.DoesNotExist:
                from django.http import Http404
                raise Http404("Quiz not found")
        
        return execute_with_retry(_get_object)

    def perform_create(self, serializer):
        def _perform_create():
            lecture_id = self.kwargs.get('lecture_pk', None)
            section_id = self.kwargs.get('section_pk', None)
            course_id = self.kwargs.get('course_pk', None)
            
            if lecture_id:
                lecture = get_object_or_404(Lecture, pk=lecture_id)
                # Check if quiz already exists for this lecture
                if Quiz.objects.filter(lecture=lecture).exists():
                    from rest_framework.exceptions import ValidationError
                    raise ValidationError("Quiz already exists for this lecture")
                
                with transaction.atomic():
                    serializer.save(
                        lecture=lecture,
                        section=lecture.section,
                        course=lecture.section.course
                    )
            elif section_id:
                section = get_object_or_404(CourseSection, pk=section_id)
                # Check if quiz already exists for this section
                if Quiz.objects.filter(section=section).exists():
                    from rest_framework.exceptions import ValidationError
                    raise ValidationError("Quiz already exists for this section")
                
                with transaction.atomic():
                    serializer.save(
                        section=section,
                        course=section.course
                    )
            elif course_id:
                course = get_object_or_404(Course, pk=course_id)
                # Check if quiz already exists for this course
                if Quiz.objects.filter(course=course).exists():
                    from rest_framework.exceptions import ValidationError
                    raise ValidationError("Quiz already exists for this course")
                
                with transaction.atomic():
                    serializer.save(course=course)
        
        return execute_with_retry(_perform_create)


class QuizQuestionViewSet(BaseModelViewSet):
    serializer_class = QuizQuestionSerializer
    permission_classes = [IsAuthenticated, CanAccessCourseContent]

    def get_queryset(self):
        def _get_queryset():
            lecture_id = self.kwargs.get('lecture_pk')
            try:
                lecture = get_object_or_404(Lecture, pk=lecture_id)
                quiz = get_object_or_404(Quiz, lecture=lecture)
                return QuizQuestion.objects.filter(quiz=quiz).order_by('order')
            except Quiz.DoesNotExist:
                return QuizQuestion.objects.none()
        
        return execute_with_retry(_get_queryset)

    def perform_create(self, serializer):
        def _perform_create():
            lecture_id = self.kwargs.get('lecture_pk')
            lecture = get_object_or_404(Lecture, pk=lecture_id)
            quiz = get_object_or_404(Quiz, lecture=lecture)
            
            last_question = QuizQuestion.objects.filter(quiz=quiz).order_by('-order').first()
            new_order = (last_question.order + 1) if last_question else 1
            
            with transaction.atomic():
                serializer.save(quiz=quiz, order=new_order)
        
        return execute_with_retry(_perform_create)


class QuizTaskViewSet(BaseModelViewSet):
    serializer_class = QuizTaskSerializer
    permission_classes = [IsAuthenticated, CanAccessCourseContent]

    def get_queryset(self):
        def _get_queryset():
            lecture_id = self.kwargs.get('lecture_pk')
            try:
                lecture = get_object_or_404(Lecture, pk=lecture_id)
                quiz = get_object_or_404(Quiz, lecture=lecture)
                return QuizTask.objects.filter(quiz=quiz).order_by('order')
            except Quiz.DoesNotExist:
                return QuizTask.objects.none()
        
        return execute_with_retry(_get_queryset)

    def perform_create(self, serializer):
        def _perform_create():
            lecture_id = self.kwargs.get('lecture_pk')
            lecture = get_object_or_404(Lecture, pk=lecture_id)
            quiz = get_object_or_404(Quiz, lecture=lecture)
            
            last_task = QuizTask.objects.filter(quiz=quiz).order_by('-order').first()
            new_order = (last_task.order + 1) if last_task else 1
            
            with transaction.atomic():
                serializer.save(quiz=quiz, order=new_order)
        
        return execute_with_retry(_perform_create)


class CourseQAItemsView(generics.ListAPIView):
    """
    Get all Q&A items for a course - only for enrolled users
    """
    serializer_class = QaItemSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        course_slug = self.kwargs.get('slug')
        course = get_object_or_404(Course, slug=course_slug)
        
        # Check if user is enrolled
        from enrollments.models import Enrollment
        if not Enrollment.objects.filter(student=self.request.user, course=course).exists():
            return QaItem.objects.none()
        
        return QaItem.objects.filter(
            lecture__section__course=course
        ).select_related('asked_by', 'lecture').order_by('-created_at')

#-----------------------------------------------------------#

class CourseQuizzesView(generics.ListAPIView):
    """
    Get all quizzes for a course with questions and tasks - only for enrolled users
    """
    serializer_class = QuizSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        course_slug = self.kwargs.get('slug')
        course = get_object_or_404(Course, slug=course_slug)
        
        # Check if user is enrolled
        from enrollments.models import Enrollment
        if not Enrollment.objects.filter(student=self.request.user, course=course).exists():
            return Quiz.objects.none()
        
        return Quiz.objects.filter(course=course).prefetch_related(
            Prefetch('questions', queryset=QuizQuestion.objects.order_by('order')),
            Prefetch('tasks', queryset=QuizTask.objects.order_by('order'))
        )


class LectureQAItemsView(generics.ListCreateAPIView):
    """
    Get or create Q&A items for a specific lecture - only for enrolled users
    """
    serializer_class = QaItemSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        lecture_id = self.kwargs.get('lecture_id')
        lecture = get_object_or_404(Lecture, id=lecture_id)
        
        # Check if user is enrolled in the course
        from enrollments.models import Enrollment
        if not Enrollment.objects.filter(
            student=self.request.user, 
            course=lecture.section.course
        ).exists():
            return QaItem.objects.none()
        
        return QaItem.objects.filter(lecture=lecture).select_related('asked_by').order_by('-created_at')
    
    def perform_create(self, serializer):
        lecture_id = self.kwargs.get('lecture_id')
        lecture = get_object_or_404(Lecture, id=lecture_id)
        
        # Check if user is enrolled
        from enrollments.models import Enrollment
        if not Enrollment.objects.filter(
            student=self.request.user, 
            course=lecture.section.course
        ).exists():
            raise PermissionDenied("You must be enrolled to ask questions")
        
        serializer.save(lecture=lecture, asked_by=self.request.user)


class LectureQuizView(generics.RetrieveAPIView):
    """
    Get quiz for a specific lecture with questions and tasks - only for enrolled users
    """
    serializer_class = QuizSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        lecture_id = self.kwargs.get('lecture_id')
        lecture = get_object_or_404(Lecture, id=lecture_id)
        
        # Check if user is enrolled
        from enrollments.models import Enrollment
        if not Enrollment.objects.filter(
            student=self.request.user, 
            course=lecture.section.course
        ).exists():
            raise PermissionDenied("You must be enrolled to access quizzes")
        
        return get_object_or_404(
            Quiz.objects.prefetch_related(
                Prefetch('questions', queryset=QuizQuestion.objects.order_by('order')),
                Prefetch('tasks', queryset=QuizTask.objects.order_by('order'))
            ),
            lecture=lecture
        )


# Enhanced serializers that include full data
class FullQaItemSerializer(QaItemSerializer):
    """Full Q&A serializer with all details for enrolled users"""
    asked_by = UserSerializer(read_only=True)
    lecture = serializers.SerializerMethodField()
    
    class Meta(QaItemSerializer.Meta):
        fields = QaItemSerializer.Meta.fields + ['lecture']
    
    def get_lecture(self, obj):
        return {
            'id': obj.lecture.id,
            'title': obj.lecture.title,
            'section': {
                'id': obj.lecture.section.id,
                'title': obj.lecture.section.title
            }
        }


class EnrolledCourseDetailView(generics.RetrieveAPIView):
    """
    Comprehensive course details for enrolled users only
    Includes all content, Q&A, quizzes with questions/tasks
    """
    serializer_class = CourseDetailSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'slug'
    lookup_url_kwarg = 'slug'

    def get_queryset(self):
        # Only return courses the user is enrolled in
        from enrollments.models import Enrollment
        return Course.objects.filter(
            enrollments__student=self.request.user
        ).prefetch_related(
            'sections__lectures__resources',
            'sections__lectures__qa_items',
            'sections__lectures__project_tools',
            'sections__lectures__quiz__questions',
            'sections__lectures__quiz__tasks'
        )

class UserCourseProgressView(generics.RetrieveAPIView):
    """
    Returns user's progress in a specific course
    """
    serializer_class = serializers.Serializer  # We'll use a custom response
    permission_classes = [IsAuthenticated]
    lookup_field = 'slug'
    lookup_url_kwarg = 'slug'

    def get(self, request, *args, **kwargs):
        course = self.get_object()
        
        try:
            from enrollments.models import Enrollment
            enrollment = Enrollment.objects.get(
                student=request.user,
                course=course
            )
            
            # Calculate progress
            total_lectures = course.sections.aggregate(
                total=models.Count('lectures')
            )['total'] or 0
            
            completed_lectures = enrollment.progress.completed_lectures.count()
            progress_percent = round((completed_lectures / total_lectures) * 100 if total_lectures > 0 else 0)
            
            # Get time spent
            time_spent_minutes = enrollment.progress.time_spent_minutes
            
            return Response({
                'course_id': course.id,
                'course_title': course.title,
                'total_lectures': total_lectures,
                'completed_lectures': completed_lectures,
                'progress_percent': progress_percent,
                'time_spent_minutes': time_spent_minutes,
                'last_accessed': enrollment.progress.last_accessed
            })
            
        except Enrollment.DoesNotExist:
            return Response(
                {'detail': 'You are not enrolled in this course'},
                status=status.HTTP_403_FORBIDDEN
            )

    def get_queryset(self):
        return Course.objects.all()

class UserCourseQAView(generics.ListAPIView):
    """
    Returns all Q&A items contributed by the current user in a course
    """
    serializer_class = FullQaItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        course_slug = self.kwargs.get('slug')
        course = get_object_or_404(Course, slug=course_slug)
        
        # Verify enrollment
        from enrollments.models import Enrollment
        if not Enrollment.objects.filter(student=self.request.user, course=course).exists():
            raise PermissionDenied("You must be enrolled to view your Q&A")
        
        return QaItem.objects.filter(
            lecture__section__course=course,
            asked_by=self.request.user
        ).select_related('lecture', 'lecture__section').order_by('-created_at')