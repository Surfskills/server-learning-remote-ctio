from rest_framework import viewsets, generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.decorators import action
from django.contrib.auth import get_user_model
from django.db.models import Q, Count, Prefetch

from core.utils import success_response, error_response
from .models import UserProfile, UserActivity, UserPreference, UserRole, UserDevice
from .serializers import (
    UserDetailSerializer, UserProfileSerializer,
    UserActivitySerializer, UserPreferenceSerializer,
    UserRoleSerializer, UserDeviceSerializer
)
from core.permissions import IsAdminUser, IsInstructor, IsStudent

User = get_user_model()

class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Viewset for user management
    """
    queryset = User.objects.all().select_related(
        'extended_profile',
        'preferences'
    ).prefetch_related(
        'roles',
        'devices'
    )
    serializer_class = UserDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            if not self.request.user.is_staff:
                return [IsAuthenticated()]
        return super().get_permissions()

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Admin users can see all users
        if self.request.user.is_staff or self.request.user.is_superuser:
            return queryset
        
        # Instructors can see students enrolled in their courses
        if self.request.user.user_type == 'INSTRUCTOR':
            from enrollments.models import Enrollment
            
            # Get all students enrolled in instructor's courses
            enrolled_student_ids = Enrollment.objects.filter(
                course__instructor=self.request.user
            ).values_list('student_id', flat=True).distinct()
            
            return queryset.filter(
                Q(pk=self.request.user.pk) |  # Include themselves
                Q(id__in=enrolled_student_ids)  # Include their students
            )
        
        # Regular users can only see themselves
        return queryset.filter(pk=self.request.user.pk)

    @action(detail=False, methods=['get'])
    def me(self, request):
        """
        Get detailed information about the current user
        """
        serializer = self.get_serializer(request.user)
        return success_response(data=serializer.data)

    @action(detail=False, methods=['get'])
    def my_students(self, request):
        """
        Get all students enrolled in instructor's courses
        """
        if request.user.user_type != 'INSTRUCTOR':
            return error_response(
                message="Only instructors can access this endpoint",
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        from enrollments.models import Enrollment
        from courses.models import Course
        
        try:
            # Get instructor's courses
            instructor_courses = Course.objects.filter(instructor=request.user)
            
            # Get enrollments for these courses with student details
            enrollments = Enrollment.objects.filter(
                course__instructor=request.user
            ).select_related(
                'student__extended_profile',
                'course'
            ).prefetch_related(
                'progress'
            ).order_by('student__first_name', 'student__last_name')
            
            # Group students by course
            students_by_course = {}
            all_students = {}
            
            for enrollment in enrollments:
                student = enrollment.student
                course = enrollment.course
                
                # Add to all students dict (avoid duplicates)
                if student.id not in all_students:
                    all_students[student.id] = {
                        'id': student.id,
                        'first_name': student.first_name,
                        'last_name': student.last_name,
                        'email': student.email,
                        'user_type': student.user_type,
                        'is_active': student.is_active,
                        'date_joined': student.date_joined,
                        'profile': UserProfileSerializer(
                            getattr(student, 'extended_profile', None)
                        ).data if hasattr(student, 'extended_profile') else None,
                        'courses': []
                    }
                
                # Add course enrollment info to student
                try:
                    progress = enrollment.progress
                    progress_stats = progress.get_progress_stats()
                except:
                    progress_stats = {
                        'progress_percentage': 0,
                        'completed_lectures': 0,
                        'total_lectures': 0,
                        'is_completed': False
                    }
                
                course_info = {
                    'course_id': course.id,
                    'course_title': course.title,
                    'course_slug': course.slug,
                    'enrolled_at': enrollment.enrolled_at,
                    'completed': enrollment.completed,
                    'completed_at': enrollment.completed_at,
                    'progress': progress_stats
                }
                
                all_students[student.id]['courses'].append(course_info)
                
                # Group by course
                if course.id not in students_by_course:
                    students_by_course[course.id] = {
                        'course_id': course.id,
                        'course_title': course.title,
                        'course_slug': course.slug,
                        'students': []
                    }
                
                student_course_data = all_students[student.id].copy()
                student_course_data['enrollment'] = course_info
                students_by_course[course.id]['students'].append(student_course_data)
            
            # Calculate summary statistics
            total_students = len(all_students)
            total_enrollments = enrollments.count()
            completed_enrollments = enrollments.filter(completed=True).count()
            active_students = len([s for s in all_students.values() if s['is_active']])
            
            response_data = {
                'summary': {
                    'total_unique_students': total_students,
                    'total_enrollments': total_enrollments,
                    'completed_enrollments': completed_enrollments,
                    'completion_rate': round((completed_enrollments / total_enrollments * 100), 2) if total_enrollments > 0 else 0,
                    'active_students': active_students,
                    'instructor_courses_count': instructor_courses.count()
                },
                'students': list(all_students.values()),
                'students_by_course': list(students_by_course.values())
            }
            
            # Apply pagination if requested
            page_size = request.query_params.get('page_size')
            if page_size:
                try:
                    page_size = int(page_size)
                    page = int(request.query_params.get('page', 1))
                    start = (page - 1) * page_size
                    end = start + page_size
                    
                    response_data['students'] = response_data['students'][start:end]
                    response_data['pagination'] = {
                        'page': page,
                        'page_size': page_size,
                        'total_pages': (total_students + page_size - 1) // page_size,
                        'total_items': total_students,
                        'has_next': end < total_students,
                        'has_previous': page > 1
                    }
                except (ValueError, TypeError):
                    pass  # Invalid pagination params, ignore
            
            return success_response(
                data=response_data,
                message=f"Retrieved {total_students} students from {total_enrollments} enrollments"
            )
            
        except Exception as e:
            return error_response(
                message=f"Error retrieving students: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def course_students(self, request):
        """
        Get students for a specific course (instructor only)
        """
        if request.user.user_type != 'INSTRUCTOR':
            return error_response(
                message="Only instructors can access this endpoint",
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        course_id = request.query_params.get('course_id')
        course_slug = request.query_params.get('course_slug')
        
        if not course_id and not course_slug:
            return error_response(
                message="Either course_id or course_slug is required",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        from enrollments.models import Enrollment
        from courses.models import Course
        
        try:
            # Verify instructor owns the course
            course_filter = Q(instructor=request.user)
            if course_id:
                course_filter &= Q(id=course_id)
            if course_slug:
                course_filter &= Q(slug=course_slug)
            
            try:
                course = Course.objects.get(course_filter)
            except Course.DoesNotExist:
                return error_response(
                    message="Course not found or you don't have permission to view it",
                    status_code=status.HTTP_404_NOT_FOUND
                )
            
            # Get enrollments for this course
            enrollments = Enrollment.objects.filter(
                course=course
            ).select_related(
                'student__extended_profile'
            ).prefetch_related(
                'progress'
            ).order_by('student__first_name', 'student__last_name')
            
            students_data = []
            for enrollment in enrollments:
                student = enrollment.student
                
                # Get progress statistics
                try:
                    progress = enrollment.progress
                    progress_stats = progress.get_progress_stats()
                except:
                    progress_stats = {
                        'progress_percentage': 0,
                        'completed_lectures': 0,
                        'total_lectures': 0,
                        'is_completed': False
                    }
                
                student_data = {
                    'id': student.id,
                    'first_name': student.first_name,
                    'last_name': student.last_name,
                    'email': student.email,
                    'is_active': student.is_active,
                    'date_joined': student.date_joined,
                    'profile': UserProfileSerializer(
                        getattr(student, 'extended_profile', None)
                    ).data if hasattr(student, 'extended_profile') else None,
                    'enrollment': {
                        'id': enrollment.id,
                        'enrolled_at': enrollment.enrolled_at,
                        'completed': enrollment.completed,
                        'completed_at': enrollment.completed_at,
                        'progress': progress_stats
                    }
                }
                students_data.append(student_data)
            
            response_data = {
                'course': {
                    'id': course.id,
                    'title': course.title,
                    'slug': course.slug
                },
                'students': students_data,
                'summary': {
                    'total_students': len(students_data),
                    'completed_students': sum(1 for s in students_data if s['enrollment']['completed']),
                    'average_progress': round(sum(s['enrollment']['progress']['progress_percentage'] for s in students_data) / len(students_data), 2) if students_data else 0
                }
            }
            
            return success_response(
                data=response_data,
                message=f"Retrieved {len(students_data)} students for course '{course.title}'"
            )
            
        except Exception as e:
            return error_response(
                message=f"Error retrieving course students: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def student_progress(self, request, pk=None):
        """
        Get detailed progress for a specific student (instructor only)
        """
        if request.user.user_type != 'INSTRUCTOR':
            return error_response(
                message="Only instructors can access this endpoint",
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        from enrollments.models import Enrollment
        
        try:
            # Get the student
            student = self.get_object()
            
            # Verify instructor has access to this student
            enrollments = Enrollment.objects.filter(
                student=student,
                course__instructor=request.user
            ).select_related(
                'course',
                'progress'
            ).prefetch_related(
                'progress__completed_lectures__section'
            )
            
            if not enrollments.exists():
                return error_response(
                    message="You don't have permission to view this student's progress",
                    status_code=status.HTTP_403_FORBIDDEN
                )
            
            student_courses = []
            for enrollment in enrollments:
                try:
                    progress = enrollment.progress
                    progress_stats = progress.get_progress_stats()
                    
                    # Get completed lectures details
                    completed_lectures = []
                    for lecture in progress.completed_lectures.all():
                        completed_lectures.append({
                            'id': lecture.id,
                            'title': lecture.title,
                            'section': lecture.section.title,
                            'order': lecture.order
                        })
                    
                except:
                    progress_stats = {
                        'progress_percentage': 0,
                        'completed_lectures': 0,
                        'total_lectures': 0,
                        'is_completed': False
                    }
                    completed_lectures = []
                
                course_data = {
                    'course': {
                        'id': enrollment.course.id,
                        'title': enrollment.course.title,
                        'slug': enrollment.course.slug
                    },
                    'enrollment': {
                        'id': enrollment.id,
                        'enrolled_at': enrollment.enrolled_at,
                        'completed': enrollment.completed,
                        'completed_at': enrollment.completed_at
                    },
                    'progress': progress_stats,
                    'completed_lectures': completed_lectures
                }
                student_courses.append(course_data)
            
            response_data = {
                'student': {
                    'id': student.id,
                    'first_name': student.first_name,
                    'last_name': student.last_name,
                    'email': student.email,
                    'is_active': student.is_active,
                    'date_joined': student.date_joined,
                    'profile': UserProfileSerializer(
                        getattr(student, 'extended_profile', None)
                    ).data if hasattr(student, 'extended_profile') else None
                },
                'courses': student_courses,
                'summary': {
                    'total_courses': len(student_courses),
                    'completed_courses': sum(1 for c in student_courses if c['enrollment']['completed']),
                    'average_progress': round(sum(c['progress']['progress_percentage'] for c in student_courses) / len(student_courses), 2) if student_courses else 0
                }
            }
            
            return success_response(
                data=response_data,
                message=f"Retrieved progress for student {student.first_name} {student.last_name}"
            )
            
        except Exception as e:
            return error_response(
                message=f"Error retrieving student progress: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['patch', 'put'])
    def update_profile(self, request):
        """
        Update current user's profile - creates if doesn't exist
        """
        try:
            # Get or create user profile
            profile, created = UserProfile.objects.get_or_create(
                user=request.user,
                defaults={}
            )
            
            # Update profile with provided data
            serializer = UserProfileSerializer(profile, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                action_type = "created" if created else "updated"
                return success_response(
                    data=serializer.data,
                    message=f"Profile {action_type} successfully"
                )
            else:
                return error_response(
                    message="Invalid data",
                    errors=serializer.errors,
                    status_code=status.HTTP_400_BAD_REQUEST
                )
        except Exception as e:
            return error_response(
                message="Error updating profile",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
    @action(detail=True, methods=['get'], url_path='bio')
    def get_bio(self, request, pk=None):
        """
        Get instructor bio
        """
        user = self.get_object()
        
        # Check if the user is an instructor
        if not user.user_type == 'INSTRUCTOR':
            return error_response(
                message="User is not an instructor",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        # Get or create profile
        profile, created = UserProfile.objects.get_or_create(
            user=user,
            defaults={'bio': 'No bio available'}
        )
        
        return success_response(data={
            'bio': profile.bio or 'No bio available',
            'avatarUrl': request.build_absolute_uri(profile.profile_picture.url) if profile.profile_picture else None
        })

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """
        Admin endpoint to activate a user
        """
        if not request.user.is_staff:
            return error_response(
                message="Permission denied",
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        user = self.get_object()
        user.is_active = True
        user.save()
        return success_response(message="User activated successfully")

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """
        Admin endpoint to deactivate a user
        """
        if not request.user.is_staff:
            return error_response(
                message="Permission denied",
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        user = self.get_object()
        user.is_active = False
        user.save()
        return success_response(message="User deactivated successfully")

class UserProfileViewSet(viewsets.ModelViewSet):
    """
    Viewset for user profile management
    """
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.request.user.is_staff:
            queryset = queryset.filter(user=self.request.user)
        return queryset

    def get_object(self):
        """
        Override to handle getting current user's profile
        """
        if self.kwargs.get('pk') == 'me':
            # Get or create profile for current user
            profile, created = UserProfile.objects.get_or_create(
                user=self.request.user,
                defaults={}
            )
            return profile
        return super().get_object()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        """
        Ensure user can only update their own profile
        """
        if not self.request.user.is_staff:
            serializer.save(user=self.request.user)
        else:
            serializer.save()

# Rest of your views remain the same...
class UserPreferenceViewSet(viewsets.ModelViewSet):
    """
    Viewset for user preference management
    """
    queryset = UserPreference.objects.all()
    serializer_class = UserPreferenceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.request.user.is_staff:
            queryset = queryset.filter(user=self.request.user)
        return queryset

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class UserRoleViewSet(viewsets.ModelViewSet):
    """
    Viewset for user role management
    """
    queryset = UserRole.objects.all()
    serializer_class = UserRoleSerializer
    permission_classes = [IsAdminUser]

    def perform_create(self, serializer):
        serializer.save(granted_by=self.request.user)

class UserDeviceViewSet(viewsets.ModelViewSet):
    """
    Viewset for user device management
    """
    queryset = UserDevice.objects.all()
    serializer_class = UserDeviceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.request.user.is_staff:
            queryset = queryset.filter(user=self.request.user)
        return queryset

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class UserActivityView(generics.ListAPIView):
    """
    View for user activity logs
    """
    serializer_class = UserActivitySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = UserActivity.objects.filter(user=self.request.user)
        activity_type = self.request.query_params.get('type')
        if activity_type:
            queryset = queryset.filter(activity_type=activity_type)
        return queryset.order_by('-created_at')

class InstructorListView(generics.ListAPIView):
    """
    List all instructors
    """
    serializer_class = UserDetailSerializer
    permission_classes = [IsAuthenticated]
    queryset = User.objects.filter(user_type='INSTRUCTOR').select_related(
        'extended_profile',
        'preferences'
    ).prefetch_related(
        'roles',
        'devices'
    )

class StudentListView(generics.ListAPIView):
    """
    List all students - Admin only or instructor's students
    """
    serializer_class = UserDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = User.objects.filter(user_type='STUDENT').select_related(
            'extended_profile',
            'preferences'
        ).prefetch_related(
            'roles',
            'devices'
        )
        
        # Admin can see all students
        if self.request.user.is_staff or self.request.user.is_superuser:
            return queryset
        
        # Instructors can see only their enrolled students
        if self.request.user.user_type == 'INSTRUCTOR':
            from enrollments.models import Enrollment
            
            enrolled_student_ids = Enrollment.objects.filter(
                course__instructor=self.request.user
            ).values_list('student_id', flat=True).distinct()
            
            return queryset.filter(id__in=enrolled_student_ids)
        
        # Regular users get empty queryset
        return queryset.none()

    def get_permissions(self):
        if self.request.method == 'GET':
            return [IsAuthenticated()]
        return [IsAdminUser()]