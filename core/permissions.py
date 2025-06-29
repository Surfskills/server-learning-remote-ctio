from rest_framework import permissions
from rest_framework.permissions import BasePermission

from courses.models import Course
from enrollments.models import Enrollment



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
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Get the course from the object
        course = None
        
        # If object is a Course
        if hasattr(obj, 'instructor'):
            course = obj
        # If object has a direct course attribute
        elif hasattr(obj, 'course'):
            course = obj.course
        # If object is a Lecture (access through section)
        elif hasattr(obj, 'section') and hasattr(obj.section, 'course'):
            course = obj.section.course
        else:
            return False
            
        return Enrollment.objects.filter(
            student=request.user, 
            course=course
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
            course = Course.objects.get(pk=course_pk)
            # Check if user is enrolled in the course
            return Enrollment.objects.filter(
                student=request.user,
                course=course
            ).exists()
        except Course.DoesNotExist:
            return False

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # If the object has a course attribute, check enrollment
        if hasattr(obj, 'course'):
            return Enrollment.objects.filter(
                student=request.user,
                course=obj.course
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
    - Enrolled students (any authenticated user enrolled in the course)
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
        
        try:
            course = Course.objects.get(id=course_id)
            
            # Check if user is the course instructor
            if course.instructor == request.user:
                return True
            
            # Check if any authenticated user is enrolled in the course
            return Enrollment.objects.filter(
                course=course, 
                student=request.user
            ).exists()
            
        except Course.DoesNotExist:
            return False

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
            
        # Admin users have full access
        if request.user.is_staff or request.user.is_superuser:
            return True
        
        # Get the course from the object - FIXED VERSION
        course = self._get_course_from_object(obj)
        
        if not course:
            return False
        
        # Check if user is the course instructor
        if course.instructor == request.user:
            return True
        
        # Check if any authenticated user is enrolled
        return Enrollment.objects.filter(
            course=course, 
            student=request.user
        ).exists()
    
    def _get_course_from_object(self, obj):
        """
        Extract course from various object types with proper error handling
        """
        # Direct course object
        if hasattr(obj, 'instructor'):
            return obj
        
        # Objects with direct course attribute
        if hasattr(obj, 'course'):
            return obj.course
        
        # Lecture objects - access through section
        if hasattr(obj, 'section') and hasattr(obj.section, 'course'):
            return obj.section.course
        
        # For objects with enrollment
        if hasattr(obj, 'enrollment') and hasattr(obj.enrollment, 'course'):
            return obj.enrollment.course
        
        return None


class CanAccessEnrolledCourses(BasePermission):
    """
    Permission that allows any authenticated user to access courses they are enrolled in.
    This is a general permission for course access based on enrollment.
    """
    message = "You must be enrolled in this course to access it."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
            
        # Admin users have full access
        if request.user.is_staff or request.user.is_superuser:
            return True
        
        # Get course_pk from URL kwargs
        course_pk = view.kwargs.get('course_pk') or view.kwargs.get('pk')
        if not course_pk:
            return True  # Let it pass to object-level permission
        
        try:
            course = Course.objects.get(pk=course_pk)
            
            # Check if user is the course instructor
            if course.instructor == request.user:
                return True
            
            # Check if authenticated user is enrolled in the course
            return Enrollment.objects.filter(
                course=course,
                student=request.user
            ).exists()
            
        except Course.DoesNotExist:
            return False

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
            
        # Admin users have full access
        if request.user.is_staff or request.user.is_superuser:
            return True
        
        # Get the course from the object - FIXED VERSION
        course = self._get_course_from_object(obj)
        
        if not course:
            return False
        
        # Check if user is the course instructor
        if course.instructor == request.user:
            return True
        
        # Check if authenticated user is enrolled
        return Enrollment.objects.filter(
            course=course,
            student=request.user
        ).exists()
    
    def _get_course_from_object(self, obj):
        """
        Extract course from various object types with proper error handling
        """
        # Direct course object
        if hasattr(obj, 'instructor'):
            return obj
        
        # Objects with direct course attribute
        if hasattr(obj, 'course'):
            return obj.course
        
        # Lecture objects - access through section
        if hasattr(obj, 'section') and hasattr(obj.section, 'course'):
            return obj.section.course
        
        # For objects with enrollment
        if hasattr(obj, 'enrollment') and hasattr(obj.enrollment, 'course'):
            return obj.enrollment.course
        
        return None


# === NEW CALENDAR APP SPECIFIC PERMISSIONS ===

class CanAccessCalendarEvent(BasePermission):
    """
    Custom permission for calendar event access.
    Allows access to:
    - Admin users (staff/superuser)
    - Event creators
    - Event attendees
    - Course instructors (for course events)
    - Enrolled students (for course events) - any authenticated user enrolled
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
                
            # Check if any authenticated user is enrolled in the course
            if Enrollment.objects.filter(
                course=obj.course, 
                student=request.user
            ).exists():
                return True
        
        return False


class CanAccessContentReleaseSchedule(BasePermission):
    """
    Custom permission for content release schedule access.
    Allows access to:
    - Admin users (staff/superuser)
    - Course instructors
    - Schedule creators
    - Enrolled students (read-only) - any authenticated user enrolled
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
        
        # Check if any authenticated user is enrolled in the course (read-only access)
        if request.method in permissions.SAFE_METHODS:
            if Enrollment.objects.filter(
                course=obj.course, 
                student=request.user
            ).exists():
                return True
        
        return False


class CanAccessContentReleaseRule(BasePermission):
    """
    Custom permission for content release rule access.
    Allows access to:
    - Admin users (staff/superuser)
    - Course instructors
    - Schedule creators
    - Enrolled students (read-only) - any authenticated user enrolled
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
        
        # Check if any authenticated user is enrolled in the course (read-only access)
        if request.method in permissions.SAFE_METHODS:
            if Enrollment.objects.filter(
                course=obj.schedule.course, 
                student=request.user
            ).exists():
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


# core/permissions.py

from rest_framework import permissions
from django.db.models import Q

class CanViewEnrollmentProgress(permissions.BasePermission):
    """
    Custom permission to only allow users to view enrollment progress
    for their own enrollments or courses they instruct.
    """
    
    def has_permission(self, request, view):
        # Must be authenticated
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # Allow superusers and staff to access everything
        if request.user.is_superuser or request.user.is_staff:
            return True
        
        # Get the course based on the object type
        course = self._get_course_from_object(obj)
        
        if course is None:
            return False
        
        # Check if user is the instructor of the course
        if hasattr(course, 'instructor') and course.instructor == request.user:
            return True
        
        # Check if user has an enrollment for this course
        from users.models import Enrollment  # Import here to avoid circular imports
        return Enrollment.objects.filter(
            student=request.user,
            course=course
        ).exists()
    
    def _get_course_from_object(self, obj):
        """
        Extract the course from different object types - FIXED VERSION
        """
        # Direct course access
        if hasattr(obj, 'course'):
            return obj.course
        
        # For Lecture objects - access through section
        if hasattr(obj, 'section') and hasattr(obj.section, 'course'):
            return obj.section.course
        
        # For Enrollment objects
        if hasattr(obj, 'enrollment') and hasattr(obj.enrollment, 'course'):
            return obj.enrollment.course
        
        # For objects that ARE courses
        if hasattr(obj, 'instructor'):  # Assuming Course has instructor field
            return obj
        
        # For CourseProgress objects
        if hasattr(obj, 'enrollment'):
            return getattr(obj.enrollment, 'course', None)
        
        # For Section objects - try to get course directly or via course_id
        if hasattr(obj, 'course_id') and not hasattr(obj, 'course'):
            try:
                from courses.models import Course
                return Course.objects.get(id=obj.course_id)
            except (Course.DoesNotExist, AttributeError):
                pass
        
        return None


# Alternative implementation with more explicit object type checking
class CanViewEnrollmentProgressDetailed(permissions.BasePermission):
    """
    More detailed version with explicit object type checking - FIXED VERSION
    """
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser or request.user.is_staff:
            return True
        
        # Import models here to avoid circular imports
        from users.models import Enrollment
        from courses.models import Course, Section, Lecture
        
        course = None
        
        # Determine object type and extract course
        if isinstance(obj, Course):
            course = obj
        elif isinstance(obj, Enrollment):
            course = obj.course
        elif isinstance(obj, Section):
            course = obj.course
        elif isinstance(obj, Lecture):
            # FIXED: Lecture objects access course through section
            if hasattr(obj, 'section') and hasattr(obj.section, 'course'):
                course = obj.section.course
        elif hasattr(obj, 'enrollment'):  # CourseProgress
            course = obj.enrollment.course
        elif hasattr(obj, 'course'):  # Generic objects with course attribute
            course = obj.course
        
        if course is None:
            return False
        
        # Check if user is the instructor
        if hasattr(course, 'instructor') and course.instructor == request.user:
            return True
        
        # Check if user is enrolled in the course
        return Enrollment.objects.filter(
            student=request.user,
            course=course
        ).exists()


# If you want to add logging for debugging
class CanViewEnrollmentProgressWithLogging(permissions.BasePermission):
    """
    Version with logging for debugging permission issues - FIXED VERSION
    """
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        import logging
        logger = logging.getLogger(__name__)
        
        logger.debug(f"Checking permission for user {request.user} on object {obj} (type: {type(obj)})")
        
        if request.user.is_superuser or request.user.is_staff:
            logger.debug("Permission granted: User is superuser/staff")
            return True
        
        try:
            course = self._get_course_from_object(obj)
            logger.debug(f"Extracted course: {course}")
            
            if course is None:
                logger.debug("Permission denied: Could not extract course from object")
                return False
            
            # Check instructor
            if hasattr(course, 'instructor') and course.instructor == request.user:
                logger.debug("Permission granted: User is course instructor")
                return True
            
            # Check enrollment
            from users.models import Enrollment
            is_enrolled = Enrollment.objects.filter(
                student=request.user,
                course=course
            ).exists()
            
            if is_enrolled:
                logger.debug("Permission granted: User is enrolled in course")
                return True
            else:
                logger.debug("Permission denied: User is not enrolled in course")
                return False
                
        except Exception as e:
            logger.error(f"Error in permission check: {e}")
            return False
    
    def _get_course_from_object(self, obj):
        """Extract course from object with error handling - FIXED VERSION"""
        try:
            # Direct course access
            if hasattr(obj, 'course'):
                return obj.course
            
            # Lecture -> Section -> Course (FIXED)
            if hasattr(obj, 'section'):
                if hasattr(obj.section, 'course'):
                    return obj.section.course
            
            # Enrollment -> Course
            if hasattr(obj, 'enrollment'):
                if hasattr(obj.enrollment, 'course'):
                    return obj.enrollment.course
            
            # Object is a course itself
            if hasattr(obj, 'instructor'):
                return obj
                
        except AttributeError as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"AttributeError in _get_course_from_object: {e}")
        
        return None