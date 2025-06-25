from rest_framework import permissions
from rest_framework.permissions import BasePermission


class IsAdminUser(BasePermission):
    """
    Allows access only to admin users (staff or superuser).
    """
    def has_permission(self, request, view):
        return request.user and (request.user.is_staff or request.user.is_superuser)


class IsInstructor(BasePermission):
    """
    Allows access only to instructor users.
    """
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and 
            getattr(request.user, 'user_type', None) == 'INSTRUCTOR'
        )


class IsStudent(BasePermission):
    """
    Allows access only to student users.
    """
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and 
            getattr(request.user, 'user_type', None) == 'STUDENT'
        )


class IsAdminOrCourseInstructor(BasePermission):
    message = "You must be an admin or the course instructor to perform this action."

    def has_permission(self, request, view):
        # First check if user is authenticated
        if not request.user or not request.user.is_authenticated:
            return False
            
        # ADMIN users should have full access to everything
        if request.user.is_staff or request.user.is_superuser:
            return True
            
        # For section creation, check if user is the course instructor
        if view.action == 'create':
            course_id = view.kwargs.get('course_pk')
            if not course_id:
                print("No course_pk in kwargs")
                return False
                
            try:
                from courses.models import Course
                course = Course.objects.get(pk=course_id)
                print(f"Checking if {request.user} is instructor of {course}")
                return course.instructor == request.user
            except Course.DoesNotExist:
                print(f"Course {course_id} does not exist")
                return False
                
        return True  # Allow other actions if they pass object permissions


class IsCourseInstructor(BasePermission):
    """
    Allows access only if user is the instructor of the course.
    """
    def has_object_permission(self, request, view, obj):
        if obj is None:
            return False
        return obj.instructor == request.user
    
    def has_course_permission_by_id(self, request, course_id):
        """
        Check if user is instructor of a course by course ID.
        """
        if not request.user or not request.user.is_authenticated:
            return False
            
        try:
            from courses.models import Course
            course = Course.objects.get(id=course_id)
            return course.instructor == request.user
        except Course.DoesNotExist:
            return False


class IsEnrolledStudent(BasePermission):
    """
    Allows access only if user is enrolled in the course.
    """
    def has_object_permission(self, request, view, obj):
        from enrollments.models import Enrollment
        return Enrollment.objects.filter(
            student=request.user, 
            course=obj if hasattr(obj, 'instructor') else obj.course
        ).exists()


class IsCourseEnrolled(BasePermission):
    """
    Permission to check if user is enrolled in the course.
    Works with URL kwargs to get course_pk.
    """
    message = "You must be enrolled in this course to access this resource."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Get course_pk from URL kwargs
        course_pk = view.kwargs.get('course_pk')
        if not course_pk:
            return False
        
        try:
            from courses.models import Course
            from enrollments.models import Enrollment
            
            course = Course.objects.get(pk=course_pk)
            # Check if user is enrolled in the course
            return Enrollment.objects.filter(
                student=request.user,
                course=course,
                is_active=True  # Assuming you have an is_active field
            ).exists()
        except Course.DoesNotExist:
            return False

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        
        from enrollments.models import Enrollment
        
        # If the object has a course attribute, check enrollment
        if hasattr(obj, 'course'):
            return Enrollment.objects.filter(
                student=request.user,
                course=obj.course,
                is_active=True
            ).exists()
        
        return True


class IsInstructorOrAdmin(BasePermission):
    """
    Allows access to instructors or admin users.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Admin users have full access
        if request.user.is_staff or request.user.is_superuser:
            return True
        
        # Check if user is an instructor
        return getattr(request.user, 'user_type', None) == 'INSTRUCTOR'


class CanAccessCourseContent(BasePermission):
    """
    Custom permission for course content access.
    Allows access to:
    - Admin users (staff/superuser)
    - Course instructors
    - Enrolled students
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
            
        # Admin users have full access
        if request.user.is_staff or request.user.is_superuser:
            return True
        
        course_id = view.kwargs.get('course_pk')
        if not course_id:
            return False
        
        # Check if user is the course instructor
        if getattr(request.user, 'user_type', None) == 'INSTRUCTOR':
            from courses.models import Course
            return Course.objects.filter(id=course_id, instructor=request.user).exists()
        
        # Check if user is enrolled in the course
        from enrollments.models import Enrollment
        return Enrollment.objects.filter(course_id=course_id, student=request.user).exists()

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
            
        # Admin users have full access
        if request.user.is_staff or request.user.is_superuser:
            return True
        
        # Get the course from the object
        course = obj if hasattr(obj, 'instructor') else obj.course
        
        # Check if user is the course instructor
        if course.instructor == request.user:
            return True
        
        # Check if user is enrolled
        from enrollments.models import Enrollment
        return Enrollment.objects.filter(course=course, student=request.user).exists()


# === NEW CALENDAR APP SPECIFIC PERMISSIONS ===

class CanAccessCalendarEvent(BasePermission):
    """
    Custom permission for calendar event access.
    Allows access to:
    - Admin users (staff/superuser)
    - Event creators
    - Event attendees
    - Course instructors (for course events)
    - Enrolled students (for course events)
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
            
        # Admin users have full access
        if request.user.is_staff or request.user.is_superuser:
            return True
        
        return True  # Allow authenticated users, specific checks in has_object_permission

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
            
        # Admin users have full access
        if request.user.is_staff or request.user.is_superuser:
            return True
        
        # Check if user created the event
        if obj.created_by == request.user:
            return True
        
        # Check if user is an attendee
        if obj.attendees.filter(id=request.user.id).exists():
            return True
        
        # If it's a course event, check course permissions
        if obj.course:
            # Check if user is the course instructor
            if obj.course.instructor == request.user:
                return True
                
            # Check if user is enrolled in the course
            from enrollments.models import Enrollment
            if Enrollment.objects.filter(course=obj.course, student=request.user, is_active=True).exists():
                return True
        
        return False


class CanAccessContentReleaseSchedule(BasePermission):
    """
    Custom permission for content release schedule access.
    Allows access to:
    - Admin users (staff/superuser)
    - Course instructors
    - Schedule creators
    - Enrolled students (read-only)
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
            
        # Admin users have full access
        if request.user.is_staff or request.user.is_superuser:
            return True
        
        return True  # Allow authenticated users, specific checks in has_object_permission

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
            
        # Admin users have full access
        if request.user.is_staff or request.user.is_superuser:
            return True
        
        # Check if user created the schedule
        if obj.created_by == request.user:
            return True
        
        # Check if user is the course instructor
        if obj.course.instructor == request.user:
            return True
        
        # Check if user is enrolled in the course (read-only access)
        if request.method in permissions.SAFE_METHODS:
            from enrollments.models import Enrollment
            if Enrollment.objects.filter(course=obj.course, student=request.user, is_active=True).exists():
                return True
        
        return False


class CanAccessContentReleaseRule(BasePermission):
    """
    Custom permission for content release rule access.
    Allows access to:
    - Admin users (staff/superuser)
    - Course instructors
    - Schedule creators
    - Enrolled students (read-only)
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
            
        # Admin users have full access
        if request.user.is_staff or request.user.is_superuser:
            return True
        
        return True  # Allow authenticated users, specific checks in has_object_permission

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
            
        # Admin users have full access
        if request.user.is_staff or request.user.is_superuser:
            return True
        
        # Check if user created the schedule
        if obj.schedule.created_by == request.user:
            return True
        
        # Check if user is the course instructor
        if obj.schedule.course.instructor == request.user:
            return True
        
        # Check if user is enrolled in the course (read-only access)
        if request.method in permissions.SAFE_METHODS:
            from enrollments.models import Enrollment
            if Enrollment.objects.filter(course=obj.schedule.course, student=request.user, is_active=True).exists():
                return True
        
        return False


class CanAccessStudentProgressOverride(BasePermission):
    """
    Custom permission for student progress override access.
    Allows access to:
    - Admin users (staff/superuser)
    - Course instructors
    - Schedule creators
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
            
        # Admin users have full access
        if request.user.is_staff or request.user.is_superuser:
            return True
        
        # Only instructors and admins can manage overrides
        return getattr(request.user, 'user_type', None) == 'INSTRUCTOR'

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
            
        # Admin users have full access
        if request.user.is_staff or request.user.is_superuser:
            return True
        
        # Check if user created the schedule
        if obj.rule.schedule.created_by == request.user:
            return True
        
        # Check if user is the course instructor
        if obj.rule.schedule.course.instructor == request.user:
            return True
        
        return False


class IsOwnerOrAdmin(BasePermission):
    """
    Custom permission to only allow owners of an object or admin users to access it.
    Assumes the model instance has an 'user' attribute.
    """
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
            
        # Admin users have full access
        if request.user.is_staff or request.user.is_superuser:
            return True
        
        # Check if user owns the object
        return obj.user == request.user


class CanManageCalendarNotifications(BasePermission):
    """
    Custom permission for calendar notification management.
    Users can only manage their own notifications, admins can manage all.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
            
        # Admin users have full access
        if request.user.is_staff or request.user.is_superuser:
            return True
        
        return True  # Allow authenticated users

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
            
        # Admin users have full access
        if request.user.is_staff or request.user.is_superuser:
            return True
        
        # Users can only manage their own notifications
        return obj.user == request.user