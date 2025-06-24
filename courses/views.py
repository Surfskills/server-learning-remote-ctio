# views.py
from rest_framework import viewsets, generics, status, permissions
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from django.db.models import Q, Prefetch
from django.db import transaction  # Add this import
from django.shortcuts import get_object_or_404

from .models import (
    Course, CourseCategory, CourseSection, Lecture, LectureResource,
    QaItem, ProjectTool, Quiz, QuizQuestion, QuizTask
)
from .serializers import (
    CourseSerializer, CourseCategorySerializer, CourseSectionSerializer,
    LectureSerializer, LectureResourceSerializer, LectureCreateSerializer,
    AdminCourseSerializer, QaItemSerializer, ProjectToolSerializer,
    QuizSerializer, QuizQuestionSerializer, QuizTaskSerializer
)
from core.views import BaseModelViewSet
from core.utils import success_response, error_response
from core.permissions import IsAdminUser, IsInstructor, IsAdminOrCourseInstructor, CanAccessCourseContent
from authentication.models import User


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
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsAdminOrCourseInstructor()]
        elif self.action in ['enroll', 'update_status', 'reorder_sections']:
            return [IsAuthenticated()]
        return [IsAuthenticated()]

    def get_queryset(self):
        queryset = super().filter_queryset(super().get_queryset())
        # Admin users can see all courses, regular users only see published ones
        if not (self.request.user.is_staff or self.request.user.is_superuser):
            queryset = queryset.filter(is_published=True)
        return queryset
    
    def perform_create(self, serializer):
        # Check if instructor_id is provided in the data
        instructor_id = self.request.data.get('instructor_id')
        
        if instructor_id:
            # Admin or staff can assign any instructor
            if self.request.user.is_staff or self.request.user.is_superuser:
                # Let the serializer handle the instructor_id validation and assignment
                serializer.save()
            else:
                # Regular users can only create courses for themselves
                serializer.save(instructor=self.request.user)
        else:
            # No instructor_id provided, default to current user
            serializer.save(instructor=self.request.user)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def enroll(self, request, pk=None):
        course = self.get_object()
        from enrollments.models import Enrollment, CourseProgress
        
        if Enrollment.objects.filter(student=request.user, course=course).exists():
            return error_response('Already enrolled', status_code=status.HTTP_400_BAD_REQUEST)
        
        enrollment = Enrollment.objects.create(
            student=request.user,
            course=course
        )
        CourseProgress.objects.create(enrollment=enrollment)
        return success_response('Enrolled successfully', status_code=status.HTTP_201_CREATED)

    @action(detail=True, methods=['patch'], permission_classes=[IsAuthenticated])
    def update_status(self, request, pk=None):
        """Update course publication status"""
        course = self.get_object()
        
        # Admin users or course instructor can update status
        if not (request.user.is_staff or request.user.is_superuser or course.instructor == request.user):
            return error_response('Permission denied', status_code=status.HTTP_403_FORBIDDEN)
        
        is_published = request.data.get('is_published')
        if is_published is None:
            return error_response('is_published field is required', status_code=status.HTTP_400_BAD_REQUEST)
        
        course.is_published = is_published
        course.save()
        return success_response('Course status updated successfully')
    
    @action(detail=True, methods=['patch'], url_path='archive')
    def archive(self, request, pk=None):
        """Toggle course archive status"""
        course = self.get_object()
        is_active = request.data.get('is_active', True)
        
        # Update the course
        course.is_active = is_active
        course.save()
        
        # Serialize and return updated course
        serializer = self.get_serializer(course)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def reorder_sections(self, request, pk=None):
        """Reorder sections within a course"""
        course = self.get_object()
        
        # Check permissions
        if not (request.user.is_staff or request.user.is_superuser or course.instructor == request.user):
            return error_response('Permission denied', status_code=status.HTTP_403_FORBIDDEN)
        
        sections_data = request.data.get('sections', [])
        
        if not sections_data:
            return error_response('sections data is required', status_code=status.HTTP_400_BAD_REQUEST)
        
        try:
            with transaction.atomic():
                for section_data in sections_data:
                    section = CourseSection.objects.get(id=section_data['id'], course=course)
                    section.order = section_data['order']
                    section.save()
            return success_response('Sections reordered successfully', status_code=status.HTTP_200_OK)
        except CourseSection.DoesNotExist:
            return error_response('One or more sections not found', status_code=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return error_response(str(e), status_code=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def sections(self, request, pk=None):
        """Get sections for a specific course with optimized queries"""
        course = self.get_object()
        sections = course.sections.prefetch_related(
            Prefetch('lectures', queryset=Lecture.objects.order_by('order'))
        ).order_by('order')
        
        sections_data = [{
            'id': section.id,
            'title': section.title,
            'order': section.order,
            'lectures': [{
                'id': lecture.id,
                'title': lecture.title,
                'duration': lecture.duration,
                'preview_available': lecture.preview_available
            } for lecture in section.lectures.all()]
        } for section in sections]
        
        return Response({'results': sections_data})


class AdminCourseViewSet(BaseModelViewSet, CourseFilterMixin):
    """Admin-specific course management with additional fields and controls"""
    queryset = Course.objects.all()
    serializer_class = AdminCourseSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get_queryset(self):
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


class CourseCategoryViewSet(BaseModelViewSet):
    queryset = CourseCategory.objects.all()
    serializer_class = CourseCategorySerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsAdminUser()]
        return [IsAuthenticated()]


class CourseSearchView(generics.ListAPIView):
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None  # Disable pagination for search results

    def get_queryset(self):
        queryset = Course.objects.filter(is_published=True)
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


class CourseDetailView(generics.RetrieveAPIView):
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated]
    queryset = Course.objects.all()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


import time
from django.db import transaction, OperationalError, IntegrityError

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
        course_id = self.kwargs.get('course_pk')
        if not course_id:
            return CourseSection.objects.none()
        return CourseSection.objects.filter(course_id=course_id).order_by('order')

    def create(self, request, *args, **kwargs):
        """
        Create a new course section with protection against:
        - Duplicate titles within the same course
        - Order conflicts
        - Race conditions
        """
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

    def perform_update(self, serializer):
        """Update section with protection against duplicate titles"""
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
        
        serializer.save()

    @action(detail=True, methods=['post'])
    def reorder(self, request, course_pk=None, pk=None):
        """Reorder sections with proper transaction isolation"""
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

class LectureViewSet(BaseModelViewSet):
    serializer_class = LectureSerializer
    permission_classes = [IsAuthenticated, CanAccessCourseContent]

    def get_queryset(self):
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

    def get_serializer_class(self):
        if self.action == 'create':
            return LectureCreateSerializer
        return super().get_serializer_class()

    def perform_create(self, serializer):
        section = get_object_or_404(CourseSection, pk=self.kwargs.get('section_pk'))
        last_lecture = Lecture.objects.filter(section=section).order_by('-order').first()
        new_order = (last_lecture.order + 1) if last_lecture else 1
        
        # Save the lecture and get the instance
        lecture = serializer.save(section=section, order=new_order)
        
        # Return the created lecture instance so it's available in the response
        return lecture

    def create(self, request, *args, **kwargs):
        """Override create to ensure proper response with ID"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Create the lecture
        lecture = self.perform_create(serializer)
        
        # Use the main serializer to format the response
        response_serializer = LectureSerializer(lecture, context={'request': request})
        
        headers = self.get_success_headers(response_serializer.data)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=True, methods=['post'])
    def add_qa(self, request, pk=None, section_pk=None):
        lecture = self.get_object()
        serializer = QaItemSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save(lecture=lecture, asked_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def add_project_tool(self, request, pk=None, section_pk=None):
        lecture = self.get_object()
        serializer = ProjectToolSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(lecture=lecture)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def create_quiz(self, request, pk=None, section_pk=None):
        lecture = self.get_object()
        serializer = QuizSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save(
                lecture=lecture,
                section=lecture.section,
                course=lecture.section.course
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def quiz(self, request, pk=None, section_pk=None):
        lecture = self.get_object()
        quiz = get_object_or_404(Quiz, lecture=lecture)
        serializer = QuizSerializer(quiz, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def reorder(self, request, pk=None, section_pk=None):
        lecture = self.get_object()
        new_order = request.data.get('order')
        
        if new_order is None:
            return error_response('Order is required', status_code=status.HTTP_400_BAD_REQUEST)
        
        try:
            lecture.order = new_order
            lecture.save()
            return success_response('Lecture reordered successfully')
        except Exception as e:
            return error_response(str(e), status_code=status.HTTP_400_BAD_REQUEST)

class LectureResourceViewSet(BaseModelViewSet):
    serializer_class = LectureResourceSerializer
    permission_classes = [IsAuthenticated, CanAccessCourseContent]

    def get_queryset(self):
        lecture_id = self.kwargs.get('lecture_pk')
        return LectureResource.objects.filter(lecture_id=lecture_id)

    def perform_create(self, serializer):
        lecture = get_object_or_404(Lecture, pk=self.kwargs.get('lecture_pk'))
        serializer.save(lecture=lecture)

class QaItemViewSet(BaseModelViewSet):
    serializer_class = QaItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        lecture_id = self.kwargs.get('lecture_pk')
        return QaItem.objects.filter(lecture_id=lecture_id).select_related('asked_by')

    def perform_create(self, serializer):
        lecture = get_object_or_404(Lecture, pk=self.kwargs.get('lecture_pk'))
        serializer.save(lecture=lecture, asked_by=self.request.user)

    @action(detail=True, methods=['post'])
    def upvote(self, request, pk=None, lecture_pk=None):
        qa_item = self.get_object()
        qa_item.upvotes += 1
        qa_item.save()
        return Response({'upvotes': qa_item.upvotes})

    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None, lecture_pk=None):
        qa_item = self.get_object()
        qa_item.resolved = True
        qa_item.save()
        return Response({'resolved': qa_item.resolved})

class ProjectToolViewSet(BaseModelViewSet):
    serializer_class = ProjectToolSerializer
    permission_classes = [IsAuthenticated, CanAccessCourseContent]

    def get_queryset(self):
        lecture_id = self.kwargs.get('lecture_pk')
        return ProjectTool.objects.filter(lecture_id=lecture_id)

    def perform_create(self, serializer):
        lecture = get_object_or_404(Lecture, pk=self.kwargs.get('lecture_pk'))
        serializer.save(lecture=lecture)

class QuizViewSet(BaseModelViewSet):
    serializer_class = QuizSerializer
    permission_classes = [IsAuthenticated, CanAccessCourseContent]

    def get_queryset(self):
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
    
    @action(detail=True, methods=['get'])
    def retrieve_full(self, request, course_pk=None, section_pk=None, lecture_pk=None):
        quiz = self.get_object()
        questions = quiz.questions.all()
        tasks = quiz.tasks.all()
        
        return Response({
            'quiz': QuizSerializer(quiz).data,
            'questions': QuizQuestionSerializer(questions, many=True).data,
            'tasks': QuizTaskSerializer(tasks, many=True).data
        })
    
    def get_object(self):
        """Override get_object to handle one-to-one relationship with lecture"""
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

    def perform_create(self, serializer):
        lecture_id = self.kwargs.get('lecture_pk', None)
        section_id = self.kwargs.get('section_pk', None)
        course_id = self.kwargs.get('course_pk', None)
        
        if lecture_id:
            lecture = get_object_or_404(Lecture, pk=lecture_id)
            # Check if quiz already exists for this lecture
            if Quiz.objects.filter(lecture=lecture).exists():
                from rest_framework.exceptions import ValidationError
                raise ValidationError("Quiz already exists for this lecture")
            
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
            
            serializer.save(course=course)

class QuizQuestionViewSet(BaseModelViewSet):
    serializer_class = QuizQuestionSerializer
    permission_classes = [IsAuthenticated, CanAccessCourseContent]

    def get_queryset(self):
        lecture_id = self.kwargs.get('lecture_pk')
        try:
            lecture = get_object_or_404(Lecture, pk=lecture_id)
            quiz = get_object_or_404(Quiz, lecture=lecture)
            return QuizQuestion.objects.filter(quiz=quiz).order_by('order')
        except Quiz.DoesNotExist:
            return QuizQuestion.objects.none()

    def perform_create(self, serializer):
        lecture_id = self.kwargs.get('lecture_pk')
        lecture = get_object_or_404(Lecture, pk=lecture_id)
        quiz = get_object_or_404(Quiz, lecture=lecture)
        
        last_question = QuizQuestion.objects.filter(quiz=quiz).order_by('-order').first()
        new_order = (last_question.order + 1) if last_question else 1
        serializer.save(quiz=quiz, order=new_order)


class QuizTaskViewSet(BaseModelViewSet):
    serializer_class = QuizTaskSerializer
    permission_classes = [IsAuthenticated, CanAccessCourseContent]

    def get_queryset(self):
        lecture_id = self.kwargs.get('lecture_pk')
        try:
            lecture = get_object_or_404(Lecture, pk=lecture_id)
            quiz = get_object_or_404(Quiz, lecture=lecture)
            return QuizTask.objects.filter(quiz=quiz).order_by('order')
        except Quiz.DoesNotExist:
            return QuizTask.objects.none()

    def perform_create(self, serializer):
        lecture_id = self.kwargs.get('lecture_pk')
        lecture = get_object_or_404(Lecture, pk=lecture_id)
        quiz = get_object_or_404(Quiz, lecture=lecture)
        
        last_task = QuizTask.objects.filter(quiz=quiz).order_by('-order').first()
        new_order = (last_task.order + 1) if last_task else 1
        serializer.save(quiz=quiz, order=new_order)