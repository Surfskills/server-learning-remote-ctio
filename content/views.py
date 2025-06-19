# from rest_framework import viewsets, status
# from rest_framework.response import Response
# from rest_framework.permissions import IsAuthenticated, IsAdminUser
# from rest_framework.decorators import action

# from courses.models import Course

# from .models import CourseSection, Lecture, LectureResource
# from .serializers import (
#     CourseSectionSerializer,
#     LectureSerializer,
#     LectureResourceSerializer,
#     LectureCreateSerializer
# )
# from core.views import BaseModelViewSet
# from core.utils import success_response, error_response
# from core.permissions import IsCourseInstructor, CanAccessCourseContent

# class CourseSectionViewSet(BaseModelViewSet):
#     serializer_class = CourseSectionSerializer
#     permission_classes = [IsAuthenticated, IsCourseInstructor]

#     def get_queryset(self):
#         course_id = self.kwargs.get('course_pk')
#         return CourseSection.objects.filter(course_id=course_id).order_by('order')

#     def perform_create(self, serializer):
#         course = Course.objects.get(pk=self.kwargs.get('course_pk'))
#         serializer.save(course=course)

#     @action(detail=True, methods=['post'])
#     def reorder(self, request, pk=None, course_pk=None):
#         section = self.get_object()
#         new_order = request.data.get('order')
        
#         if new_order is None:
#             return error_response('Order is required', status_code=status.HTTP_400_BAD_REQUEST)
        
#         try:
#             section.to(new_order)
#             return success_response('Section reordered successfully')
#         except ValueError as e:
#             return error_response(str(e), status_code=status.HTTP_400_BAD_REQUEST)

# class LectureViewSet(BaseModelViewSet):
#     serializer_class = LectureSerializer
#     permission_classes = [IsAuthenticated, CanAccessCourseContent]

#     def get_queryset(self):
#         section_id = self.kwargs.get('section_pk')
#         return Lecture.objects.filter(section_id=section_id).order_by('order')

#     def get_serializer_class(self):
#         if self.action == 'create':
#             return LectureCreateSerializer
#         return super().get_serializer_class()

#     def perform_create(self, serializer):
#         section = CourseSection.objects.get(pk=self.kwargs.get('section_pk'))
#         last_lecture = Lecture.objects.filter(section=section).order_by('-order').first()
#         new_order = (last_lecture.order + 1) if last_lecture else 1
#         serializer.save(section=section, order=new_order)

#     @action(detail=True, methods=['post'])
#     def reorder(self, request, pk=None, section_pk=None):
#         lecture = self.get_object()
#         new_order = request.data.get('order')
        
#         if new_order is None:
#             return error_response('Order is required', status_code=status.HTTP_400_BAD_REQUEST)
        
#         try:
#             lecture.to(new_order)
#             return success_response('Lecture reordered successfully')
#         except ValueError as e:
#             return error_response(str(e), status_code=status.HTTP_400_BAD_REQUEST)

# class LectureResourceViewSet(BaseModelViewSet):
#     serializer_class = LectureResourceSerializer
#     permission_classes = [IsAuthenticated, CanAccessCourseContent]

#     def get_queryset(self):
#         lecture_id = self.kwargs.get('lecture_pk')
#         return LectureResource.objects.filter(lecture_id=lecture_id)

#     def perform_create(self, serializer):
#         lecture = Lecture.objects.get(pk=self.kwargs.get('lecture_pk'))
#         serializer.save(lecture=lecture)