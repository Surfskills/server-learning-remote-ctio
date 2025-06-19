from rest_framework import viewsets, generics, status, permissions
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from django.db.models import Q, Prefetch
from django.shortcuts import get_object_or_404

from .models import Course, CourseCategory, CourseSection, Lecture, LectureResource
from .serializers import (
    CourseSerializer,
    CourseCategorySerializer,
    CourseSectionSerializer,
    LectureSerializer,
    LectureResourceSerializer,
    LectureCreateSerializer,
    AdminCourseSerializer
)
from core.views import BaseModelViewSet
from core.utils import success_response, error_response
from core.permissions import (
    IsAdminUser,
    IsInstructor,

    IsAdminOrCourseInstructor,
    CanAccessCourseContent
)
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
        elif self.action in ['enroll', 'update_status']:
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


class CourseSectionViewSet(BaseModelViewSet):
    serializer_class = CourseSectionSerializer
    permission_classes = [IsAuthenticated, IsAdminOrCourseInstructor]
    lookup_field = 'pk'

    def get_queryset(self):
        course_id = self.kwargs.get('course_pk')
        if not course_id:
            return CourseSection.objects.none()
        return CourseSection.objects.filter(course_id=course_id).order_by('order')

    def perform_create(self, serializer):
        course = get_object_or_404(Course, pk=self.kwargs.get('course_pk'))
        
        # Verify permissions again for extra security
        if not (self.request.user.is_staff or 
                self.request.user.is_superuser or 
                course.instructor == self.request.user):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You don't have permission to create sections for this course.")
        
        # Calculate next order number
        last_section = CourseSection.objects.filter(course=course).order_by('-order').first()
        next_order = (last_section.order + 1) if last_section else 1
        
        serializer.save(course=course, order=next_order)

    @action(detail=True, methods=['post'])
    def reorder(self, request, course_pk=None, pk=None):
        section = self.get_object()
        new_order = request.data.get('order')
        
        if new_order is None:
            return error_response('Order is required', status_code=status.HTTP_400_BAD_REQUEST)
        
        try:
            section.order = new_order
            section.save()
            return success_response('Section reordered successfully')
        except Exception as e:
            return error_response(str(e), status_code=status.HTTP_400_BAD_REQUEST)


class LectureViewSet(BaseModelViewSet):
    serializer_class = LectureSerializer
    permission_classes = [IsAuthenticated, CanAccessCourseContent]

    def get_queryset(self):
        section_id = self.kwargs.get('section_pk')
        return Lecture.objects.filter(section_id=section_id).order_by('order')

    def get_serializer_class(self):
        if self.action == 'create':
            return LectureCreateSerializer
        return super().get_serializer_class()

    def perform_create(self, serializer):
        section = get_object_or_404(CourseSection, pk=self.kwargs.get('section_pk'))
        last_lecture = Lecture.objects.filter(section=section).order_by('-order').first()
        new_order = (last_lecture.order + 1) if last_lecture else 1
        serializer.save(section=section, order=new_order)

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