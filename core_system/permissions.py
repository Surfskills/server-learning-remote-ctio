from rest_framework.permissions import BasePermission

class IsInstructor(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type == 'INSTRUCTOR'

class IsStudent(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type == 'STUDENT'

class IsCourseInstructor(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.instructor == request.user

class IsEnrolledStudent(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.enrollments.filter(student=request.user).exists()

class CanAccessCourseContent(BasePermission):
    def has_permission(self, request, view):
        if request.user.is_staff:
            return True
        
        course_id = view.kwargs.get('course_pk')
        if not course_id:
            return False
        
        # Check if user is instructor of the course
        if request.user.user_type == 'INSTRUCTOR':
            return Course.objects.filter(id=course_id, instructor=request.user).exists()
        
        # Check if user is enrolled in the course
        return Enrollment.objects.filter(course_id=course_id, student=request.user).exists()