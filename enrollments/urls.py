from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'enrollments', views.EnrollmentViewSet, basename='enrollments')
router.register(r'admin-enrollments', views.AdminEnrollmentViewSet, basename='admin-enrollments')
router.register(r'progress', views.CourseProgressViewSet, basename='progress')

urlpatterns = [
    path('', include(router.urls)),
]