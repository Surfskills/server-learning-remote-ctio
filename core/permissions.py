from rest_framework import permissions
from rest_framework.permissions import BasePermission

from courses.models import Course
from enrollments.models import Enrollment
from authentication.models import User

# ────────────────
#  Base Permissions
# ────────────────
class IsAdminUser(BasePermission):
    """Allows access only to admin users (staff or superuser)."""
    def has_permission(self, request, view):
        return request.user and (request.user.is_staff or request.user.is_superuser)


class IsInstructor(BasePermission):
    """Allows access only to instructor users."""
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and 
            request.user.is_instructor
        )


class IsStudent(BasePermission):
    """Allows access only to student users."""
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and 
            request.user.is_student
        )


# ────────────────
#  Course Permissions
# ────────────────
class IsCourseInstructor(BasePermission):
    """Allows access only if user is the instructor of the course."""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
            
        # Admin users have full access
        if request.user.is_staff or request.user.is_superuser:
            return True
            
        # For course-specific actions
        course_id = view.kwargs.get('course_pk') or view.kwargs.get('pk')
        if course_id:
            try:
                course = Course.objects.get(pk=course_id)
                return course.instructor == request.user
            except Course.DoesNotExist:
                return False
        return True
    
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
            
        # Admin users have full access
        if request.user.is_staff or request.user.is_superuser:
            return True
            
        # Get the course from the object
        course = self._get_course_from_object(obj)
        if not course:
            return False
            
        return course.instructor == request.user
    
    def _get_course_from_object(self, obj):
        """Extract course from various object types."""
        if hasattr(obj, 'instructor'):  # Direct course object
            return obj
        if hasattr(obj, 'course'):  # Objects with course attribute
            return obj.course
        if hasattr(obj, 'section') and hasattr(obj.section, 'course'):  # Lecture objects
            return obj.section.course
        if hasattr(obj, 'enrollment') and hasattr(obj.enrollment, 'course'):
            return obj.enrollment.course
        return None


class CanAccessCourseContent(permissions.BasePermission):
    """
    Permission to check if user can access course content:
    - Admin: full access
    - Instructor: access to their own courses
    - Student: access to enrolled courses
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
            
        # Admin users have full access
        if request.user.is_staff or request.user.is_superuser:
            return True
            
        # For course-specific actions
        course_id = view.kwargs.get('course_pk') or view.kwargs.get('pk')
        if course_id:
            try:
                course = Course.objects.get(pk=course_id)
                
                # Instructors can access their own courses
                if request.user.is_instructor and course.instructor == request.user:
                    return True
                    
                # Students can access if enrolled
                if request.user.is_student:
                    return Enrollment.objects.filter(
                        student=request.user,
                        course=course
                    ).exists()
                    
            except Course.DoesNotExist:
                return False
                
        return True  # Allow other actions if they pass object permissions

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
            
        # Admin users have full access
        if request.user.is_staff or request.user.is_superuser:
            return True
        
        # Get the course from the object
        course = self._get_course_from_object(obj)
        
        if not course:
            return False
        
        # Check if user is the course instructor
        if course.instructor == request.user:
            return True
        
        # Check if student is enrolled
        if request.user.is_student:
            return Enrollment.objects.filter(
                course=course, 
                student=request.user
            ).exists()
        
        return False
    
    def _get_course_from_object(self, obj):
        """Extract course from various object types."""
        if hasattr(obj, 'instructor'):
            return obj
        if hasattr(obj, 'course'):
            return obj.course
        if hasattr(obj, 'section') and hasattr(obj.section, 'course'):
            return obj.section.course
        if hasattr(obj, 'enrollment') and hasattr(obj.enrollment, 'course'):
            return obj.enrollment.course
        return None


# ────────────────
#  User Profile Permissions
# ────────────────
class IsProfileOwnerOrAdmin(BasePermission):
    """Allows access only to profile owner or admin."""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        if request.user.is_staff or request.user.is_superuser:
            return True
        return obj.user == request.user


class CanViewUserProfile(BasePermission):
    """Allows viewing of user profiles with different access levels."""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # Admin can view all
        if request.user.is_staff or request.user.is_superuser:
            return True
            
        # Users can always view their own profile
        if obj.user == request.user:
            return True
            
        # Instructors can view profiles of students enrolled in their courses
        if request.user.is_instructor:
            return Enrollment.objects.filter(
                course__instructor=request.user,
                student=obj.user
            ).exists()
            
        # Students can view instructor profiles for courses they're enrolled in
        if request.user.is_student and obj.user.is_instructor:
            return Enrollment.objects.filter(
                course__instructor=obj.user,
                student=request.user
            ).exists()
            
        return False


# ────────────────
#  User Activity Permissions
# ────────────────
class CanViewUserActivity(BasePermission):
    """Controls access to user activity logs."""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # Admin can view all
        if request.user.is_staff or request.user.is_superuser:
            return True
            
        # Users can view their own activities
        return obj.user == request.user


# ────────────────
#  User Preference Permissions
# ────────────────
class IsPreferenceOwnerOrAdmin(BasePermission):
    """Allows access only to preference owner or admin."""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        if request.user.is_staff or request.user.is_superuser:
            return True
        return obj.user == request.user


# ────────────────
#  User Role Permissions
# ────────────────
class CanManageUserRoles(BasePermission):
    """Controls who can manage user roles."""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
            
        # Only admins can manage roles
        return request.user.is_staff or request.user.is_superuser
    
    def has_object_permission(self, request, view, obj):
        # Only admins can manage roles
        return request.user.is_staff or request.user.is_superuser


# ────────────────
#  User Device Permissions
# ────────────────
class IsDeviceOwnerOrAdmin(BasePermission):
    """Allows access only to device owner or admin."""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        if request.user.is_staff or request.user.is_superuser:
            return True
        return obj.user == request.user


# ────────────────
#  Enrollment Permissions
# ────────────────

class CanViewEnrollments(BasePermission):
    """
    Permission for viewing enrollments:
    - Admin: can view all enrollments
    - Instructor: can view enrollments for their courses
    - Student: can view only their own enrollments
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
            
        # Admin users have full access
        if request.user.is_staff or request.user.is_superuser:
            return True
            
        # Instructors and students can view enrollments (filtered by queryset)
        return request.user.is_instructor or request.user.is_student
    
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
            
        # Admin users have full access
        if request.user.is_staff or request.user.is_superuser:
            return True
            
        # Instructors can view enrollments for their courses
        if request.user.is_instructor:
            return obj.course.instructor == request.user
            
        # Students can view only their own enrollments
        return obj.student == request.user
    
class CanManageEnrollments(BasePermission):
    """Controls who can manage enrollments."""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
            
        # Admin can manage all enrollments
        if request.user.is_staff or request.user.is_superuser:
            return True
            
        # Instructors can manage enrollments for their own courses
        if request.user.is_instructor:
            course_id = view.kwargs.get('course_pk')
            if course_id:
                return Course.objects.filter(
                    pk=course_id,
                    instructor=request.user
                ).exists()
            return True
            
        # Students can only view their own enrollments
        return request.user.is_student
    
    def has_object_permission(self, request, view, obj):
        if request.user.is_staff or request.user.is_superuser:
            return True
            
        # Instructors can manage enrollments for their own courses
        if request.user.is_instructor:
            return obj.course.instructor == request.user
            
        # Students can only view their own enrollments
        return obj.student == request.user


# ────────────────
#  Composite Permissions
# ────────────────
class IsAdminOrCourseInstructor(BasePermission):
    """Allows admin or course instructor access."""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
            
        if request.user.is_staff or request.user.is_superuser:
            return True
            
        if not request.user.is_instructor:
            return False
            
        course_id = view.kwargs.get('course_pk')
        if course_id:
            return Course.objects.filter(
                pk=course_id,
                instructor=request.user
            ).exists()
            
        return True
    
    def has_object_permission(self, request, view, obj):
        if request.user.is_staff or request.user.is_superuser:
            return True
            
        course = self._get_course_from_object(obj)
        if not course:
            return False
            
        return course.instructor == request.user
    
    def _get_course_from_object(self, obj):
        if hasattr(obj, 'instructor'):
            return obj
        if hasattr(obj, 'course'):
            return obj.course
        if hasattr(obj, 'section') and hasattr(obj.section, 'course'):
            return obj.section.course
        return None


class IsInstructorOrAdmin(BasePermission):
    """Allows access to instructors or admin users."""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.is_staff or request.user.is_superuser or request.user.is_instructor


class IsStudentOrAdmin(BasePermission):
    """Allows access to students or admin users."""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.is_staff or request.user.is_superuser or request.user.is_student
    

# In your permissions.py file, add these new permissions:

class IsEbookCreatorOrAdmin(BasePermission):
    """Allows access only to ebook creators or admin users."""
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and 
            (request.user.is_ebook_creator or request.user.is_admin)
        )
class CanManageEbooks(BasePermission):
    """Controls who can create and manage ebooks."""
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
            
        # Admin users can always manage ebooks
        if request.user.is_staff or request.user.is_superuser:
            return True
            
        # Check if user has ebook creator role
        if hasattr(request.user, 'is_ebook_creator') and request.user.is_ebook_creator:
            return True
            
        # Instructors can manage if ALLOW_INSTRUCTOR_EBOOK_CREATION is True
        if (hasattr(request.user, 'is_instructor') and 
            request.user.is_instructor and 
            getattr(settings, 'ALLOW_INSTRUCTOR_EBOOK_CREATION', False)):
            return True
            
        return False
    
    def has_object_permission(self, request, view, obj):
        # Admins can manage all ebooks
        if request.user.is_staff or request.user.is_superuser:
            return True
            
        # Ebook creators can manage their own ebooks
        if (hasattr(request.user, 'is_ebook_creator') and 
            request.user.is_ebook_creator and 
            hasattr(obj, 'author')):
            return obj.author == request.user
            
        # Instructors can manage their own ebooks if allowed
        if (hasattr(request.user, 'is_instructor') and 
            request.user.is_instructor and 
            getattr(settings, 'ALLOW_INSTRUCTOR_EBOOK_CREATION', False) and 
            hasattr(obj, 'author')):
            return obj.author == request.user
            
        return False

class CanExportEbook(BasePermission):
    """Controls who can export ebooks."""
    def has_permission(self, request, view):
        # Same basic permissions as managing ebooks
        permission = CanManageEbooks()
        return permission.has_permission(request, view)
    
    def has_object_permission(self, request, view, obj):
        # Check if user can manage the ebook
        manage_perm = CanManageEbooks()
        if manage_perm.has_object_permission(request, view, obj):
            return True
            
        # Check if user is a collaborator with export permissions
        if hasattr(obj, 'ebookcollaborator_set'):
            return obj.ebookcollaborator_set.filter(
                user=request.user,
                can_export=True
            ).exists()
            
        return False

class CanUseTemplates(BasePermission):
    """Controls who can use and apply templates."""
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
            
        # Admin users can always use templates
        if request.user.is_staff or request.user.is_superuser:
            return True
            
        # Check if user has ebook creator role
        if hasattr(request.user, 'is_ebook_creator') and request.user.is_ebook_creator:
            return True
            
        # Instructors can use templates if allowed to create ebooks
        if (hasattr(request.user, 'is_instructor') and 
            request.user.is_instructor and 
            getattr(settings, 'ALLOW_INSTRUCTOR_EBOOK_CREATION', False)):
            return True
            
        return False
