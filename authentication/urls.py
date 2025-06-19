# authentication/urls.py
from django.urls import path
from .views import (
    UnifiedAuthView,
    LogoutView,
    VerifyTokenView,
    CustomTokenRefreshView,
    PasswordResetView,
    UserProfileView,
    ChangePasswordView,
    AdminListView,
    UserListView
)

urlpatterns = [
    # Authentication endpoints
    path('auth/', UnifiedAuthView.as_view(), name='unified_auth'),  # For both login and signup
    path('logout/', LogoutView.as_view(), name='logout'),
    
    # Token management
    path('auth/verify/', VerifyTokenView.as_view(), name='token_verify'),
    path('auth/refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),
    
    # Password reset
    path('password-reset/', PasswordResetView.as_view(), name='password_reset'),
    
    # User profile
    path('profile/', UserProfileView.as_view(), name='user_profile'),
    path('change-password/', ChangePasswordView.as_view(), name='change_password'),
    
    # Admin endpoints
    path('admins/', AdminListView.as_view(), name='admin_list'),
    path('users/', UserListView.as_view(), name='user_list'),
]