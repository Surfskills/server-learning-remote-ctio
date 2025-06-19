# courses/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Main router for admin and categories only
router = DefaultRouter()
router.register(r'admin/courses', views.AdminCourseViewSet, basename='admin-course')
router.register(r'course-categories', views.CourseCategoryViewSet, basename='category')

urlpatterns = [
    # Include router URLs
    path('', include(router.urls)),
    
    # Course-specific views
    path('search/', views.CourseSearchView.as_view(), name='course-search'),
    
    # Main course endpoints (manually registered to avoid conflicts)
    path('courses/', views.CourseViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='course-list'),
    
    path('courses/<uuid:pk>/', views.CourseViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='course-detail'),
    
    # Manual nested URLs for sections
    path('courses/<uuid:course_pk>/sections/', 
         views.CourseSectionViewSet.as_view({
             'get': 'list', 
             'post': 'create'
         }), 
         name='course-section-list'),
    
    path('courses/<uuid:course_pk>/sections/<uuid:pk>/', 
         views.CourseSectionViewSet.as_view({
             'get': 'retrieve', 
             'put': 'update', 
             'patch': 'partial_update', 
             'delete': 'destroy'
         }), 
         name='course-section-detail'),
    
    path('courses/<uuid:course_pk>/sections/<uuid:pk>/reorder/', 
         views.CourseSectionViewSet.as_view({'post': 'reorder'}), 
         name='course-section-reorder'),
    
    # Manual nested URLs for lectures
    path('courses/<uuid:course_pk>/sections/<uuid:section_pk>/lectures/', 
         views.LectureViewSet.as_view({
             'get': 'list', 
             'post': 'create'
         }), 
         name='section-lecture-list'),
    
    path('courses/<uuid:course_pk>/sections/<uuid:section_pk>/lectures/<uuid:pk>/', 
         views.LectureViewSet.as_view({
             'get': 'retrieve', 
             'put': 'update', 
             'patch': 'partial_update', 
             'delete': 'destroy'
         }), 
         name='section-lecture-detail'),
    
    path('courses/<uuid:course_pk>/sections/<uuid:section_pk>/lectures/<uuid:pk>/reorder/', 
         views.LectureViewSet.as_view({'post': 'reorder'}), 
         name='section-lecture-reorder'),
    
    # Manual nested URLs for lecture resources
    path('courses/<uuid:course_pk>/sections/<uuid:section_pk>/lectures/<uuid:lecture_pk>/resources/', 
         views.LectureResourceViewSet.as_view({
             'get': 'list', 
             'post': 'create'
         }), 
         name='lecture-resource-list'),
    
    path('courses/<uuid:course_pk>/sections/<uuid:section_pk>/lectures/<uuid:lecture_pk>/resources/<uuid:pk>/', 
         views.LectureResourceViewSet.as_view({
             'get': 'retrieve', 
             'put': 'update', 
             'patch': 'partial_update', 
             'delete': 'destroy'
         }), 
         name='lecture-resource-detail'),
]

# Alternative with nested routers (if you want to install drf-nested-routers)
"""
from rest_framework_nested import routers

# Main router
router = DefaultRouter()
router.register(r'courses', views.CourseViewSet, basename='course')
router.register(r'admin/courses', views.AdminCourseViewSet, basename='admin-course')
router.register(r'categories', views.CourseCategoryViewSet, basename='category')

# Nested routers
courses_router = routers.NestedDefaultRouter(router, r'courses', lookup='course')
courses_router.register(r'sections', views.CourseSectionViewSet, basename='course-sections')

sections_router = routers.NestedDefaultRouter(courses_router, r'sections', lookup='section')
sections_router.register(r'lectures', views.LectureViewSet, basename='section-lectures')

lectures_router = routers.NestedDefaultRouter(sections_router, r'lectures', lookup='lecture')
lectures_router.register(r'resources', views.LectureResourceViewSet, basename='lecture-resources')

urlpatterns = [
    path('', include(router.urls)),
    path('', include(courses_router.urls)),
    path('', include(sections_router.urls)),
    path('', include(lectures_router.urls)),
    path('search/', views.CourseSearchView.as_view(), name='course-search'),
]
"""