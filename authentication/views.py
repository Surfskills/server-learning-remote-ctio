import logging
from django.utils.decorators import method_decorator
from django.contrib.auth import login, authenticate, logout as django_logout
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenVerifyView, TokenRefreshView
from authentication.models import User, Profile
from authentication.serializers import (
    InstructorSerializer, SignInSerializer, SignUpSerializer, UserSerializer, UserProfileSerializer,
    CustomTokenVerifySerializer, CustomTokenRefreshSerializer,
    PasswordResetSerializer, UserUpdateSerializer, ChangePasswordSerializer,
    ProfileUpdateSerializer
)

# Set up a logger for this module
logger = logging.getLogger('authentication')


class UnifiedAuthView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        logger.debug(f"Received request data: {request.data}")
        
        # Check multiple possible indicators for signup
        is_signup = (
            request.data.get('is_signup', False) or 
            request.data.get('action') == 'register' or
            'confirm_password' in request.data
        )
        
        logger.debug(f"Is this a sign-up request? {is_signup}")

        if is_signup:
            signup_serializer = SignUpSerializer(data=request.data)
            if signup_serializer.is_valid():
                user = signup_serializer.save()
                logger.info(f"User {user.email} registered successfully with type: {user.user_type}")

                # Create JWT tokens
                refresh = RefreshToken.for_user(user)

                # Django session login
                login(request, user)

                return Response({
                    'user': UserSerializer(user).data,
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                    'message': 'User registered successfully'
                }, status=201)

            logger.error(f"Sign-up failed. Validation errors: {signup_serializer.errors}")
            return Response({
                'error': 'Sign-up failed',
                'details': signup_serializer.errors
            }, status=400)

        else:
            signin_serializer = SignInSerializer(data=request.data)

            try:
                signin_serializer.is_valid(raise_exception=True)
                user = signin_serializer.validated_data['user']

                logger.info(f"User {user.email} signed in successfully. User type: {user.user_type}")

                # Create JWT tokens
                refresh = RefreshToken.for_user(user)

                # Django session login
                login(request, user)

                return Response({
                    'user': UserSerializer(user).data,
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                    'message': 'Login successful'
                }, status=200)

            except ValidationError as e:
                logger.error(f"Sign-in failed. Validation error: {e.detail}")
                return Response({
                    'error': 'Sign-in failed',
                    'details': e.detail
                }, status=400)

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get('refresh')
        logger.info(f"Attempting to log out user: {request.user.email}")

        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
                logger.info(f"Refresh token blacklisted for user: {request.user.email}")
            except Exception as e:
                logger.error(f"Error blacklisting refresh token: {str(e)}")
                return Response({'error': 'Failed to blacklist token'}, status=400)

        # Django session logout
        django_logout(request)
        logger.info(f"User {request.user.email} logged out successfully.")

        return Response({"message": "Logged out successfully"}, status=200)


class VerifyTokenView(TokenVerifyView):
    """Takes a token and indicates if it is valid."""
    serializer_class = CustomTokenVerifySerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            token_value = request.data.get('token', '[TOKEN_VALUE]')
            logger.info(f"Token {token_value[:20]}... is valid.")
            return Response({'detail': 'Token is valid'}, status=200)
        except ValidationError as e:
            token_value = request.data.get('token', '[NOT_PROVIDED]')
            logger.error(f"Token validation failed for: {token_value[:20] if token_value != '[NOT_PROVIDED]' else token_value}. Validation errors: {e.detail}")
            
            if 'token' in e.detail and any('required' in str(error) for error in e.detail['token']):
                return Response({'detail': 'Token is required'}, status=400)
            else:
                return Response({'detail': 'Token is invalid or expired'}, status=401)
                
        except Exception as e:
            token_value = request.data.get('token', '[NOT_PROVIDED]')
            logger.error(f"Token verification error: {str(e)}")
            return Response({'detail': 'Token verification failed'}, status=401)


class CustomTokenRefreshView(TokenRefreshView):
    """Takes a refresh token and returns a new access token."""
    serializer_class = CustomTokenRefreshSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            refresh_token = request.data.get('refresh', '[NOT_PROVIDED]')
            logger.info(f"Successfully refreshed token for refresh token: {refresh_token[:20]}...")
            return Response(serializer.validated_data, status=200)
        except ValidationError as e:
            refresh_token = request.data.get('refresh', '[NOT_PROVIDED]')
            logger.error(f"Token refresh failed for: {refresh_token[:20] if refresh_token != '[NOT_PROVIDED]' else refresh_token}. Errors: {e.detail}")
            return Response({'detail': 'Token refresh failed'}, status=401)
        except Exception as e:
            refresh_token = request.data.get('refresh', '[NOT_PROVIDED]')
            logger.error(f"Token refresh error: {str(e)}")
            return Response({'detail': 'Token refresh failed'}, status=401)


class PasswordResetView(APIView):
    """Request password reset email"""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            email = serializer.validated_data['email']
            # Here you would implement your password reset email logic
            logger.info(f"Password reset requested for email: {email}")
            return Response({'message': 'Password reset email sent'}, status=200)
        except ValidationError as e:
            logger.error(f"Password reset request failed: {e.detail}")
            return Response({'error': 'Password reset request failed', 'details': e.detail}, status=400)


class UserProfileView(APIView):
    """Get and update user profile"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get user profile with related profile data"""
        try:
            # Ensure user has a profile
            profile, created = Profile.objects.get_or_create(user=request.user)
            if created:
                logger.info(f"Created profile for user: {request.user.email}")
            
            serializer = UserProfileSerializer(request.user)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Error fetching profile for user {request.user.email}: {str(e)}")
            return Response({'error': 'Failed to fetch profile'}, status=500)

    def patch(self, request):
        """Update user basic information"""
        serializer = UserUpdateSerializer(request.user, data=request.data, partial=True)
        try:
            serializer.is_valid(raise_exception=True)
            user = serializer.save()
            logger.info(f"User profile updated for: {user.email}")
            return Response(UserSerializer(user).data)
        except ValidationError as e:
            logger.error(f"Profile update failed for user {request.user.email}: {e.detail}")
            return Response({'error': 'Profile update failed', 'details': e.detail}, status=400)


class ProfileView(APIView):
    """Manage user's extended profile"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get user's extended profile"""
        try:
            profile, created = Profile.objects.get_or_create(user=request.user)
            if created:
                logger.info(f"Created profile for user: {request.user.email}")
            
            serializer = ProfileUpdateSerializer(profile)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Error fetching extended profile for user {request.user.email}: {str(e)}")
            return Response({'error': 'Failed to fetch profile'}, status=500)

    def patch(self, request):
        """Update user's extended profile"""
        try:
            profile, created = Profile.objects.get_or_create(user=request.user)
            serializer = ProfileUpdateSerializer(profile, data=request.data, partial=True)
            
            serializer.is_valid(raise_exception=True)
            profile = serializer.save()
            logger.info(f"Extended profile updated for user: {request.user.email}")
            return Response(ProfileUpdateSerializer(profile).data)
        except ValidationError as e:
            logger.error(f"Extended profile update failed for user {request.user.email}: {e.detail}")
            return Response({'error': 'Profile update failed', 'details': e.detail}, status=400)
        except Exception as e:
            logger.error(f"Unexpected error updating profile for user {request.user.email}: {str(e)}")
            return Response({'error': 'Failed to update profile'}, status=500)


class ChangePasswordView(APIView):
    """Change user password"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        try:
            serializer.is_valid(raise_exception=True)
            user = request.user
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            logger.info(f"Password changed for user: {user.email}")
            return Response({'message': 'Password changed successfully'}, status=200)
        except ValidationError as e:
            logger.error(f"Password change failed for user {request.user.email}: {e.detail}")
            return Response({'error': 'Password change failed', 'details': e.detail}, status=400)


class ProfileCompletionView(APIView):
    """Get and recalculate profile completion"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get current profile completion status"""
        user = request.user
        completion_percentage = user.calculate_profile_completion()
        
        return Response({
            'profile_completion_percentage': completion_percentage,
            'is_profile_complete': user.is_profile_complete,
            'user_type': user.user_type,
            'display_name': user.display_name
        })

    def post(self, request):
        """Force recalculate profile completion"""
        user = request.user
        completion_percentage = user.calculate_profile_completion()
        logger.info(f"Profile completion recalculated for user {user.email}: {completion_percentage}%")
        
        return Response({
            'message': 'Profile completion recalculated',
            'profile_completion_percentage': completion_percentage,
            'is_profile_complete': user.is_profile_complete
        })


# Admin and User list views
class AdminListView(APIView):
    """List all admin users"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Check if requesting user is admin or staff
        if not (request.user.is_admin or request.user.is_staff):
            return Response({'error': 'Permission denied'}, status=403)
        
        admins = User.objects.filter(user_type=User.Types.ADMIN)
        serializer = UserSerializer(admins, many=True)
        logger.info("Fetched list of admin users.")
        return Response(serializer.data, status=200)


class InstructorListView(APIView):
    """List all instructor users"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        instructors = User.objects.filter(user_type=User.Types.INSTRUCTOR).select_related('profile')
        serializer = InstructorSerializer(instructors, many=True)
        return Response(serializer.data, status=200)


class StudentListView(APIView):
    """List all student users"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Check if requesting user has permission
        if not (request.user.is_admin or request.user.is_instructor or request.user.is_support_agent):
            return Response({'error': 'Permission denied'}, status=403)
            
        students = User.objects.filter(user_type=User.Types.STUDENT)
        serializer = UserSerializer(students, many=True)
        logger.info("Fetched list of student users.")
        return Response(serializer.data, status=200)


class SupportAgentListView(APIView):
    """List all support agent users"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Check if requesting user is admin
        if not request.user.is_admin:
            return Response({'error': 'Permission denied'}, status=403)
            
        support_agents = User.objects.filter(user_type=User.Types.SUPPORT_AGENT)
        serializer = UserSerializer(support_agents, many=True)
        logger.info("Fetched list of support agent users.")
        return Response(serializer.data, status=200)


class UserListView(APIView):
    """List all users (admin only)"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Check if requesting user is admin
        if not request.user.is_admin:
            return Response({'error': 'Permission denied'}, status=403)
            
        users = User.objects.all().select_related('profile')
        serializer = UserSerializer(users, many=True)
        logger.info("Fetched list of all users.")
        return Response(serializer.data, status=200)