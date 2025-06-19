from rest_framework import viewsets, generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.decorators import action
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
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
                return [IsAdminUser()]
        return super().get_permissions()

    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.request.user.is_staff:
            queryset = queryset.filter(pk=self.request.user.pk)
        return queryset

    @action(detail=False, methods=['get'])
    def me(self, request):
        """
        Get detailed information about the current user
        """
        serializer = self.get_serializer(request.user)
        return success_response(data=serializer.data)

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
    List all students
    """
    serializer_class = UserDetailSerializer
    permission_classes = [IsAuthenticated]
    queryset = User.objects.filter(user_type='STUDENT').select_related(
        'extended_profile',
        'preferences'
    ).prefetch_related(
        'roles',
        'devices'
    )

    def get_permissions(self):
        if self.request.method == 'GET':
            return [IsAuthenticated()]
        return [IsAdminUser()]