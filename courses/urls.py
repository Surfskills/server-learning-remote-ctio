# urls.py
"""
Course Management URLs Configuration

This module defines URL patterns for the course management system, including:
- Course CRUD operations and management
- Course sections and lectures hierarchy
- Resources, Q&A, project tools, and quizzes
- Admin-specific course management endpoints

URL Structure:
/courses/                           - Main course endpoints
/courses/{id}/sections/             - Course sections
/courses/{id}/sections/{id}/lectures/ - Section lectures
/courses/{id}/sections/{id}/lectures/{id}/resources/ - Lecture resources
/courses/{id}/sections/{id}/lectures/{id}/qa/       - Lecture Q&A
/courses/{id}/sections/{id}/lectures/{id}/project-tools/ - Project tools
/courses/{id}/sections/{id}/lectures/{id}/quiz/     - Lecture quizzes

All IDs are UUIDs for security and consistency.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# =============================================================================
# ROUTER CONFIGURATION
# =============================================================================
# Router handles standard ViewSet endpoints automatically
router = DefaultRouter()

# Admin-only course management with extended functionality
router.register(r'admin/courses', views.AdminCourseViewSet, basename='admin-course')

# Course categories management (public read, admin write)
router.register(r'course-categories', views.CourseCategoryViewSet, basename='category')

# =============================================================================
# URL PATTERNS
# =============================================================================
urlpatterns = [
    # Include router-generated URLs
    path('', include(router.urls)),
    
    # =============================================================================
    # COURSE SEARCH & DISCOVERY
    # =============================================================================
    # GET /search/?q=term&category=id&level=beginner&language=en
    # Public course search with filters
    path('search/', views.CourseSearchView.as_view(), name='course-search'),
    
    # =============================================================================
    # MAIN COURSE ENDPOINTS
    # =============================================================================
    # Course list and creation
    # GET  /courses/           - List all published courses (or all for admins)
    # POST /courses/           - Create new course (requires authentication)
    path('courses/', views.CourseViewSet.as_view({
        'get': 'list',      # List courses with filtering and search
        'post': 'create'    # Create new course
    }), name='course-list'),
    
    # Individual course operations
    # GET    /courses/{uuid}/  - Retrieve course details
    # PUT    /courses/{uuid}/  - Full update (admin/instructor only)
    # PATCH  /courses/{uuid}/  - Partial update (admin/instructor only)
    # DELETE /courses/{uuid}/  - Delete course (admin/instructor only)
    path('courses/<uuid:pk>/', views.CourseViewSet.as_view({
        'get': 'retrieve',          # Get course details with sections/lectures
        'put': 'update',            # Full course update
        'patch': 'partial_update',  # Partial course update
        'delete': 'destroy'         # Delete course and all related content
    }), name='course-detail'),
    
    # =============================================================================
    # COURSE SECTIONS MANAGEMENT
    # =============================================================================
    # Sections within a course
    # GET  /courses/{uuid}/sections/     - List all sections in course
    # POST /courses/{uuid}/sections/     - Create new section in course
    path('courses/<uuid:course_pk>/sections/', 
         views.CourseSectionViewSet.as_view({
             'get': 'list',     # List sections ordered by 'order' field
             'post': 'create'   # Create section (auto-assigns next order number)
         }), 
         name='course-section-list'),
    
    # Individual section operations
    # GET    /courses/{uuid}/sections/{uuid}/  - Get section details
    # PUT    /courses/{uuid}/sections/{uuid}/  - Full section update
    # PATCH  /courses/{uuid}/sections/{uuid}/  - Partial section update
    # DELETE /courses/{uuid}/sections/{uuid}/  - Delete section
    path('courses/<uuid:course_pk>/sections/<uuid:pk>/', 
         views.CourseSectionViewSet.as_view({
             'get': 'retrieve',          # Get section with lectures
             'put': 'update',            # Full section update
             'patch': 'partial_update',  # Partial section update
             'delete': 'destroy'         # Delete section and all lectures
         }), 
         name='course-section-detail'),
    
    # Bulk section reordering
    # POST /courses/{uuid}/sections/reorder/
    # Body: {"sections": [{"id": "uuid", "order": 1}, {"id": "uuid", "order": 2}]}
    path('courses/<uuid:pk>/sections/reorder/', 
         views.CourseViewSet.as_view({'post': 'reorder_sections'}), 
         name='course-sections-reorder'),
    
    # =============================================================================
    # LECTURE MANAGEMENT
    # =============================================================================
    # Lectures within a section
    # GET  /courses/{uuid}/sections/{uuid}/lectures/  - List section lectures
    # POST /courses/{uuid}/sections/{uuid}/lectures/  - Create new lecture
    path('courses/<uuid:course_pk>/sections/<uuid:section_pk>/lectures/', 
         views.LectureViewSet.as_view({
             'get': 'list',     # List lectures with resources, Q&A, tools, quizzes
             'post': 'create'   # Create lecture (auto-assigns order)
         }), 
         name='section-lecture-list'),
    
    # Individual lecture operations
    # GET    /courses/{uuid}/sections/{uuid}/lectures/{uuid}/  - Get lecture details
    # PUT    /courses/{uuid}/sections/{uuid}/lectures/{uuid}/  - Full lecture update
    # PATCH  /courses/{uuid}/sections/{uuid}/lectures/{uuid}/  - Partial lecture update
    # DELETE /courses/{uuid}/sections/{uuid}/lectures/{uuid}/  - Delete lecture
    path('courses/<uuid:course_pk>/sections/<uuid:section_pk>/lectures/<uuid:pk>/', 
         views.LectureViewSet.as_view({
             'get': 'retrieve',          # Get lecture with all related content
             'put': 'update',            # Full lecture update
             'patch': 'partial_update',  # Partial lecture update
             'delete': 'destroy'         # Delete lecture and all content
         }), 
         name='section-lecture-detail'),
    
    # Individual lecture reordering
    # POST /courses/{uuid}/sections/{uuid}/lectures/{uuid}/reorder/
    # Body: {"order": 3}
    path('courses/<uuid:course_pk>/sections/<uuid:section_pk>/lectures/<uuid:pk>/reorder/', 
         views.LectureViewSet.as_view({'post': 'reorder'}), 
         name='section-lecture-reorder'),
    
    # =============================================================================
    # LECTURE RESOURCES
    # =============================================================================
    # Resources attached to a lecture (PDFs, links, files, etc.)
    # GET  /courses/{uuid}/sections/{uuid}/lectures/{uuid}/resources/  - List resources
    # POST /courses/{uuid}/sections/{uuid}/lectures/{uuid}/resources/  - Add resource
    path('courses/<uuid:course_pk>/sections/<uuid:section_pk>/lectures/<uuid:lecture_pk>/resources/', 
         views.LectureResourceViewSet.as_view({
             'get': 'list',     # List all resources for lecture
             'post': 'create'   # Add new resource to lecture
         }), 
         name='lecture-resource-list'),
    
    # Individual resource operations
    # GET    /courses/{uuid}/sections/{uuid}/lectures/{uuid}/resources/{uuid}/  - Get resource
    # PUT    /courses/{uuid}/sections/{uuid}/lectures/{uuid}/resources/{uuid}/  - Update resource
    # PATCH  /courses/{uuid}/sections/{uuid}/lectures/{uuid}/resources/{uuid}/  - Partial update
    # DELETE /courses/{uuid}/sections/{uuid}/lectures/{uuid}/resources/{uuid}/  - Delete resource
    path('courses/<uuid:course_pk>/sections/<uuid:section_pk>/lectures/<uuid:lecture_pk>/resources/<uuid:pk>/', 
         views.LectureResourceViewSet.as_view({
             'get': 'retrieve',          # Get resource details
             'put': 'update',            # Full resource update
             'patch': 'partial_update',  # Partial resource update
             'delete': 'destroy'         # Delete resource
         }), 
         name='lecture-resource-detail'),
    
    # =============================================================================
    # LECTURE Q&A SYSTEM
    # =============================================================================
    # Questions and answers for a lecture
    # GET  /courses/{uuid}/sections/{uuid}/lectures/{uuid}/qa/  - List Q&A items
    # POST /courses/{uuid}/sections/{uuid}/lectures/{uuid}/qa/  - Ask new question
    path('courses/<uuid:course_pk>/sections/<uuid:section_pk>/lectures/<uuid:lecture_pk>/qa/', 
         views.QaItemViewSet.as_view({
             'get': 'list',     # List Q&A items with user info
             'post': 'create'   # Create new question (auto-assigns to current user)
         }), 
         name='lecture-qa-list'),
    
    # Individual Q&A item operations
    # GET    /courses/{uuid}/sections/{uuid}/lectures/{uuid}/qa/{uuid}/  - Get Q&A item
    # PUT    /courses/{uuid}/sections/{uuid}/lectures/{uuid}/qa/{uuid}/  - Update Q&A
    # PATCH  /courses/{uuid}/sections/{uuid}/lectures/{uuid}/qa/{uuid}/  - Partial update
    # DELETE /courses/{uuid}/sections/{uuid}/lectures/{uuid}/qa/{uuid}/  - Delete Q&A
    path('courses/<uuid:course_pk>/sections/<uuid:section_pk>/lectures/<uuid:lecture_pk>/qa/<uuid:pk>/', 
         views.QaItemViewSet.as_view({
             'get': 'retrieve',          # Get Q&A item details
             'put': 'update',            # Full Q&A update
             'patch': 'partial_update',  # Partial Q&A update
             'delete': 'destroy'         # Delete Q&A item
         }), 
         name='lecture-qa-detail'),
    
    # Q&A interaction endpoints
    # POST /courses/{uuid}/sections/{uuid}/lectures/{uuid}/qa/{uuid}/upvote/  - Upvote question
    path('courses/<uuid:course_pk>/sections/<uuid:section_pk>/lectures/<uuid:lecture_pk>/qa/<uuid:pk>/upvote/', 
         views.QaItemViewSet.as_view({'post': 'upvote'}), 
         name='lecture-qa-upvote'),
    
    # POST /courses/{uuid}/sections/{uuid}/lectures/{uuid}/qa/{uuid}/resolve/  - Mark as resolved
    path('courses/<uuid:course_pk>/sections/<uuid:section_pk>/lectures/<uuid:lecture_pk>/qa/<uuid:pk>/resolve/', 
         views.QaItemViewSet.as_view({'post': 'resolve'}), 
         name='lecture-qa-resolve'),
    
    # =============================================================================
    # PROJECT TOOLS
    # =============================================================================
    # Tools and resources for hands-on projects
    # GET  /courses/{uuid}/sections/{uuid}/lectures/{uuid}/project-tools/  - List tools
    # POST /courses/{uuid}/sections/{uuid}/lectures/{uuid}/project-tools/  - Add tool
    path('courses/<uuid:course_pk>/sections/<uuid:section_pk>/lectures/<uuid:lecture_pk>/project-tools/', 
         views.ProjectToolViewSet.as_view({
             'get': 'list',     # List project tools for lecture
             'post': 'create'   # Add new project tool
         }), 
         name='lecture-project-tools-list'),
    
    # Individual project tool operations
    # GET    /courses/{uuid}/sections/{uuid}/lectures/{uuid}/project-tools/{uuid}/  - Get tool
    # PUT    /courses/{uuid}/sections/{uuid}/lectures/{uuid}/project-tools/{uuid}/  - Update tool
    # PATCH  /courses/{uuid}/sections/{uuid}/lectures/{uuid}/project-tools/{uuid}/  - Partial update
    # DELETE /courses/{uuid}/sections/{uuid}/lectures/{uuid}/project-tools/{uuid}/  - Delete tool
    path('courses/<uuid:course_pk>/sections/<uuid:section_pk>/lectures/<uuid:lecture_pk>/project-tools/<uuid:pk>/', 
         views.ProjectToolViewSet.as_view({
             'get': 'retrieve',          # Get project tool details
             'put': 'update',            # Full tool update
             'patch': 'partial_update',  # Partial tool update
             'delete': 'destroy'         # Delete project tool
         }), 
         name='lecture-project-tools-detail'),

    # =============================================================================
    # QUIZ SYSTEM
    # =============================================================================
    # Quiz management (one-to-one relationship with lecture)
    # GET    /courses/{uuid}/sections/{uuid}/lectures/{uuid}/quiz/  - Get lecture quiz
    # POST   /courses/{uuid}/sections/{uuid}/lectures/{uuid}/quiz/  - Create quiz for lecture
    # PUT    /courses/{uuid}/sections/{uuid}/lectures/{uuid}/quiz/  - Update entire quiz
    # PATCH  /courses/{uuid}/sections/{uuid}/lectures/{uuid}/quiz/  - Partial quiz update
    # DELETE /courses/{uuid}/sections/{uuid}/lectures/{uuid}/quiz/  - Delete quiz
    path('courses/<uuid:course_pk>/sections/<uuid:section_pk>/lectures/<uuid:lecture_pk>/quiz/', 
         views.QuizViewSet.as_view({
             'get': 'retrieve',          # Get quiz basic info
             'post': 'create',           # Create new quiz (one per lecture)
             'put': 'update',            # Full quiz update
             'patch': 'partial_update',  # Partial quiz update
             'delete': 'destroy'         # Delete quiz and all questions/tasks
         }), 
         name='lecture-quiz'),

    # Full quiz data including questions and tasks
    # GET /courses/{uuid}/sections/{uuid}/lectures/{uuid}/quiz/full/  - Get complete quiz data
    path('courses/<uuid:course_pk>/sections/<uuid:section_pk>/lectures/<uuid:lecture_pk>/quiz/full/', 
         views.QuizViewSet.as_view({'get': 'retrieve_full'}), 
         name='lecture-quiz-full'),

    # =============================================================================
    # QUIZ QUESTIONS
    # =============================================================================
    # Questions within a quiz (multiple choice, true/false, etc.)
    # GET  /courses/{uuid}/sections/{uuid}/lectures/{uuid}/quiz/questions/  - List questions
    # POST /courses/{uuid}/sections/{uuid}/lectures/{uuid}/quiz/questions/  - Add question
    path('courses/<uuid:course_pk>/sections/<uuid:section_pk>/lectures/<uuid:lecture_pk>/quiz/questions/', 
         views.QuizQuestionViewSet.as_view({
             'get': 'list',     # List quiz questions ordered by 'order'
             'post': 'create'   # Add new question (auto-assigns order)
         }), 
         name='lecture-quiz-questions-list'),

    # Individual quiz question operations
    # GET    /courses/{uuid}/sections/{uuid}/lectures/{uuid}/quiz/questions/{uuid}/  - Get question
    # PUT    /courses/{uuid}/sections/{uuid}/lectures/{uuid}/quiz/questions/{uuid}/  - Update question
    # PATCH  /courses/{uuid}/sections/{uuid}/lectures/{uuid}/quiz/questions/{uuid}/  - Partial update
    # DELETE /courses/{uuid}/sections/{uuid}/lectures/{uuid}/quiz/questions/{uuid}/  - Delete question
    path('courses/<uuid:course_pk>/sections/<uuid:section_pk>/lectures/<uuid:lecture_pk>/quiz/questions/<uuid:pk>/', 
         views.QuizQuestionViewSet.as_view({
             'get': 'retrieve',          # Get question with options
             'put': 'update',            # Full question update
             'patch': 'partial_update',  # Partial question update
             'delete': 'destroy'         # Delete question
         }), 
         name='lecture-quiz-questions-detail'),

    # =============================================================================
    # QUIZ TASKS
    # =============================================================================
    # Practical tasks within a quiz (coding challenges, projects, etc.)
    # GET  /courses/{uuid}/sections/{uuid}/lectures/{uuid}/quiz/tasks/  - List tasks
    # POST /courses/{uuid}/sections/{uuid}/lectures/{uuid}/quiz/tasks/  - Add task
    path('courses/<uuid:course_pk>/sections/<uuid:section_pk>/lectures/<uuid:lecture_pk>/quiz/tasks/', 
         views.QuizTaskViewSet.as_view({
             'get': 'list',     # List quiz tasks ordered by 'order'
             'post': 'create'   # Add new task (auto-assigns order)
         }), 
         name='lecture-quiz-tasks-list'),

    # Individual quiz task operations  
    # GET    /courses/{uuid}/sections/{uuid}/lectures/{uuid}/quiz/tasks/{uuid}/  - Get task
    # PUT    /courses/{uuid}/sections/{uuid}/lectures/{uuid}/quiz/tasks/{uuid}/  - Update task
    # PATCH  /courses/{uuid}/sections/{uuid}/lectures/{uuid}/quiz/tasks/{uuid}/  - Partial update
    # DELETE /courses/{uuid}/sections/{uuid}/lectures/{uuid}/quiz/tasks/{uuid}/  - Delete task
    path('courses/<uuid:course_pk>/sections/<uuid:section_pk>/lectures/<uuid:lecture_pk>/quiz/tasks/<uuid:pk>/', 
         views.QuizTaskViewSet.as_view({
             'get': 'retrieve',          # Get task details
             'put': 'update',            # Full task update
             'patch': 'partial_update',  # Partial task update
             'delete': 'destroy'         # Delete task
         }), 
         name='lecture-quiz-tasks-detail'),

         # Course status update
# PATCH /courses/{uuid}/status/
# Body: {"is_published": true/false}
path('courses/<uuid:pk>/update_status/', 
     views.CourseViewSet.as_view({'patch': 'update_status'}), 
     name='course-status-update'),

path('courses/<uuid:pk>/enroll/', 
     views.CourseViewSet.as_view({'post': 'enroll'}), 
     name='course-enroll'),


path('courses/<uuid:pk>/archive/', 
     views.CourseViewSet.as_view({'patch': 'archive'}), 
     name='archive'),
]



# =============================================================================
# ADDITIONAL NOTES
# =============================================================================
"""
Permission Requirements:
- Most GET endpoints: IsAuthenticated
- Course creation/modification: IsAuthenticated + IsAdminOrCourseInstructor
- Admin endpoints: IsAuthenticated + IsAdminUser
- Content access: IsAuthenticated + CanAccessCourseContent

URL Parameter Types:
- course_pk: UUID of the course
- section_pk: UUID of the course section  
- lecture_pk: UUID of the lecture
- pk: UUID of the specific resource being accessed

Common HTTP Status Codes:
- 200: Success (GET, PUT, PATCH)
- 201: Created (POST)
- 204: No Content (DELETE)
- 400: Bad Request (validation errors)
- 401: Unauthorized (not logged in)
- 403: Forbidden (insufficient permissions)
- 404: Not Found (resource doesn't exist)

Filtering & Search:
- Course list supports: status, search, category, level, language
- Q&A supports: resolved status filtering
- All lists support standard pagination

Bulk Operations:
- Section reordering: /courses/{id}/sections/reorder/
- Individual lecture reordering: /lectures/{id}/reorder/
"""