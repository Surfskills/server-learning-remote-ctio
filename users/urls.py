from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet, UserProfileViewSet,
    UserPreferenceViewSet, UserRoleViewSet,
    UserDeviceViewSet, UserActivityView,
    InstructorListView, StudentListView
)

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'profiles', UserProfileViewSet, basename='profile')
router.register(r'preferences', UserPreferenceViewSet, basename='preference')
router.register(r'roles', UserRoleViewSet, basename='role')
router.register(r'devices', UserDeviceViewSet, basename='device')

urlpatterns = [
    path('', include(router.urls)),
    path('activities/', UserActivityView.as_view(), name='user-activities'),
    path('instructors/', InstructorListView.as_view(), name='instructor-list'),
    path('students/', StudentListView.as_view(), name='student-list'),
]