"""
Course Management URLs Configuration

URL Structure:
- Public endpoints (no auth required)
- Authenticated endpoints (require login)
- Enrolled user endpoints (require course enrollment)
- Admin endpoints (require staff/admin privileges)
- Nested course structure (sections/lectures/resources)
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# =============================================================================
# ROUTER CONFIGURATION (Admin & Category endpoints)
# =============================================================================
router = DefaultRouter()
router.register(r'admin/courses', views.AdminCourseViewSet, basename='admin-course')
router.register(r'course-categories', views.CourseCategoryViewSet, basename='category')

# =============================================================================
# PUBLIC COURSE ENDPOINTS (No authentication required)
# =============================================================================
public_patterns = [
    path('search/', views.CourseSearchView.as_view(), name='course-search'),
    path('courses/<slug:slug>/detail/', views.CourseDetailView.as_view(), name='course-detail'),
    path('courses/<slug:slug>/content/', views.CourseContentView.as_view(), name='course-content'),
    path('courses/<slug:slug>/stats/', views.CourseStatsView.as_view(), name='course-stats'),
]

# =============================================================================
# AUTHENTICATED USER ENDPOINTS (Require login)
# =============================================================================
authenticated_patterns = [
    # Course CRUD
    path('courses/', views.CourseViewSet.as_view({
        'get': 'list', 'post': 'create'}), name='course-list'),
    path('courses/<uuid:pk>/', views.CourseViewSet.as_view({
        'get': 'retrieve', 'put': 'update', 
        'patch': 'partial_update', 'delete': 'destroy'}), name='course-detail'),
    
    # Course actions
    path('courses/<uuid:pk>/enroll/', 
         views.CourseViewSet.as_view({'post': 'enroll'}), name='course-enroll'),
    path('courses/<uuid:pk>/update_status/', 
         views.CourseViewSet.as_view({'patch': 'update_status'}), name='course-status-update'),
    path('courses/<uuid:pk>/archive/', 
         views.CourseViewSet.as_view({'patch': 'archive'}), name='course-archive'),
]

# =============================================================================
# ENROLLED USER ENDPOINTS (Require course enrollment)
# =============================================================================
enrolled_patterns = [
    path('courses/<slug:slug>/enrolled/', 
         views.EnrolledCourseDetailView.as_view(), name='enrolled-course-detail'),
    path('courses/<slug:slug>/my-progress/', 
         views.UserCourseProgressView.as_view(), name='user-course-progress'),
    path('courses/<slug:slug>/my-qa/', 
         views.UserCourseQAView.as_view(), name='user-course-qa'),
]

# =============================================================================
# COURSE STRUCTURE ENDPOINTS (Nested resources)
# =============================================================================
structure_patterns = [
    # Sections
    path('courses/<uuid:pk>/sections/summary/', 
     views.CourseViewSet.as_view({'get': 'sections'}), name='course-sections-summary'),
    path('courses/<uuid:course_pk>/sections/', 
         views.CourseSectionViewSet.as_view({'get': 'list', 'post': 'create'}), name='section-list'),
    path('courses/<uuid:course_pk>/sections/<uuid:pk>/', 
         views.CourseSectionViewSet.as_view({
             'get': 'retrieve', 'put': 'update', 
             'patch': 'partial_update', 'delete': 'destroy'}), name='section-detail'),
    path('courses/<uuid:course_pk>/sections/<uuid:pk>/reorder/', 
         views.CourseSectionViewSet.as_view({'post': 'reorder'}), name='section-reorder'),
    
    # Lectures
    path('courses/<uuid:course_pk>/sections/<uuid:section_pk>/lectures/', 
         views.LectureViewSet.as_view({'get': 'list', 'post': 'create'}), name='lecture-list'),
    path('courses/<uuid:course_pk>/sections/<uuid:section_pk>/lectures/<uuid:pk>/', 
         views.LectureViewSet.as_view({
             'get': 'retrieve', 'put': 'update', 
             'patch': 'partial_update', 'delete': 'destroy'}), name='lecture-detail'),
    path('courses/<uuid:course_pk>/sections/<uuid:section_pk>/lectures/<uuid:pk>/reorder/', 
         views.LectureViewSet.as_view({'post': 'reorder'}), name='lecture-reorder'),
    
    # Lecture Resources
    path('courses/<uuid:course_pk>/sections/<uuid:section_pk>/lectures/<uuid:lecture_pk>/resources/', 
         views.LectureResourceViewSet.as_view({'get': 'list', 'post': 'create'}), name='resource-list'),
    path('courses/<uuid:course_pk>/sections/<uuid:section_pk>/lectures/<uuid:lecture_pk>/resources/<uuid:pk>/', 
         views.LectureResourceViewSet.as_view({
             'get': 'retrieve', 'put': 'update', 
             'patch': 'partial_update', 'delete': 'destroy'}), name='resource-detail'),
    
    # Q&A System
    path('courses/<uuid:course_pk>/sections/<uuid:section_pk>/lectures/<uuid:lecture_pk>/qa/', 
         views.QaItemViewSet.as_view({'get': 'list', 'post': 'create'}), name='qa-list'),
    path('courses/<uuid:course_pk>/sections/<uuid:section_pk>/lectures/<uuid:lecture_pk>/qa/<uuid:pk>/', 
         views.QaItemViewSet.as_view({
             'get': 'retrieve', 'put': 'update', 
             'patch': 'partial_update', 'delete': 'destroy'}), name='qa-detail'),
    path('courses/<uuid:course_pk>/sections/<uuid:section_pk>/lectures/<uuid:lecture_pk>/qa/<uuid:pk>/upvote/', 
         views.QaItemViewSet.as_view({'post': 'upvote'}), name='qa-upvote'),
    path('courses/<uuid:course_pk>/sections/<uuid:section_pk>/lectures/<uuid:lecture_pk>/qa/<uuid:pk>/resolve/', 
         views.QaItemViewSet.as_view({'post': 'resolve'}), name='qa-resolve'),
    
    # Project Tools
    path('courses/<uuid:course_pk>/sections/<uuid:section_pk>/lectures/<uuid:lecture_pk>/project-tools/', 
         views.ProjectToolViewSet.as_view({'get': 'list', 'post': 'create'}), name='project-tools-list'),
    path('courses/<uuid:course_pk>/sections/<uuid:section_pk>/lectures/<uuid:lecture_pk>/project-tools/<uuid:pk>/', 
         views.ProjectToolViewSet.as_view({
             'get': 'retrieve', 'put': 'update', 
             'patch': 'partial_update', 'delete': 'destroy'}), name='project-tools-detail'),
    
    # Quiz System
    path('courses/<uuid:course_pk>/sections/<uuid:section_pk>/lectures/<uuid:lecture_pk>/quiz/', 
         views.QuizViewSet.as_view({
             'get': 'retrieve', 'post': 'create', 
             'put': 'update', 'patch': 'partial_update', 
             'delete': 'destroy'}), name='quiz-detail'),
    path('courses/<uuid:course_pk>/sections/<uuid:section_pk>/lectures/<uuid:lecture_pk>/quiz/full/', 
         views.QuizViewSet.as_view({'get': 'retrieve_full'}), name='quiz-full'),
    
    # Quiz Questions
    path('courses/<uuid:course_pk>/sections/<uuid:section_pk>/lectures/<uuid:lecture_pk>/quiz/questions/', 
         views.QuizQuestionViewSet.as_view({'get': 'list', 'post': 'create'}), name='quiz-questions'),
    path('courses/<uuid:course_pk>/sections/<uuid:section_pk>/lectures/<uuid:lecture_pk>/quiz/questions/<uuid:pk>/', 
         views.QuizQuestionViewSet.as_view({
             'get': 'retrieve', 'put': 'update', 
             'patch': 'partial_update', 'delete': 'destroy'}), name='quiz-question-detail'),
    
    # Quiz Tasks
    path('courses/<uuid:course_pk>/sections/<uuid:section_pk>/lectures/<uuid:lecture_pk>/quiz/tasks/', 
         views.QuizTaskViewSet.as_view({'get': 'list', 'post': 'create'}), name='quiz-tasks'),
    path('courses/<uuid:course_pk>/sections/<uuid:section_pk>/lectures/<uuid:lecture_pk>/quiz/tasks/<uuid:pk>/', 
         views.QuizTaskViewSet.as_view({
             'get': 'retrieve', 'put': 'update', 
             'patch': 'partial_update', 'delete': 'destroy'}), name='quiz-task-detail'),
]

# =============================================================================
# COMBINED URL PATTERNS
# =============================================================================
urlpatterns = [
    path('', include(router.urls)),
    *public_patterns,
    *authenticated_patterns, 
    *enrolled_patterns,
    *structure_patterns,
]