# urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'admin/courses', views.AdminCourseViewSet, basename='admin-course')
router.register(r'course-categories', views.CourseCategoryViewSet, basename='category')

urlpatterns = [
    path('', include(router.urls)),
    path('search/', views.CourseSearchView.as_view(), name='course-search'),
    
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
    
    # Sections
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
    
    # Lectures
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
    
    # Lecture resources
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
    
    # Q&A
    path('courses/<uuid:course_pk>/sections/<uuid:section_pk>/lectures/<uuid:lecture_pk>/qa/', 
         views.QaItemViewSet.as_view({
             'get': 'list', 
             'post': 'create'
         }), 
         name='lecture-qa-list'),
    
    path('courses/<uuid:course_pk>/sections/<uuid:section_pk>/lectures/<uuid:lecture_pk>/qa/<uuid:pk>/', 
         views.QaItemViewSet.as_view({
             'get': 'retrieve', 
             'put': 'update', 
             'patch': 'partial_update', 
             'delete': 'destroy'
         }), 
         name='lecture-qa-detail'),
    
    path('courses/<uuid:course_pk>/sections/<uuid:section_pk>/lectures/<uuid:lecture_pk>/qa/<uuid:pk>/upvote/', 
         views.QaItemViewSet.as_view({'post': 'upvote'}), 
         name='lecture-qa-upvote'),
    
    path('courses/<uuid:course_pk>/sections/<uuid:section_pk>/lectures/<uuid:lecture_pk>/qa/<uuid:pk>/resolve/', 
         views.QaItemViewSet.as_view({'post': 'resolve'}), 
         name='lecture-qa-resolve'),
    
    # Project tools
    path('courses/<uuid:course_pk>/sections/<uuid:section_pk>/lectures/<uuid:lecture_pk>/project-tools/', 
         views.ProjectToolViewSet.as_view({
             'get': 'list', 
             'post': 'create'
         }), 
         name='lecture-project-tools-list'),
    
    path('courses/<uuid:course_pk>/sections/<uuid:section_pk>/lectures/<uuid:lecture_pk>/project-tools/<uuid:pk>/', 
         views.ProjectToolViewSet.as_view({
             'get': 'retrieve', 
             'put': 'update', 
             'patch': 'partial_update', 
             'delete': 'destroy'
         }), 
         name='lecture-project-tools-detail'),


# Quiz (one-to-one with lecture)
path('courses/<uuid:course_pk>/sections/<uuid:section_pk>/lectures/<uuid:lecture_pk>/quiz/', 
     views.QuizViewSet.as_view({
         'get': 'retrieve',
         'post': 'create',
         'put': 'update',
         'patch': 'partial_update',
         'delete': 'destroy'
     }), 
     name='lecture-quiz'),

path('courses/<uuid:course_pk>/sections/<uuid:section_pk>/lectures/<uuid:lecture_pk>/quiz/full/', 
     views.QuizViewSet.as_view({'get': 'retrieve_full'}), 
     name='lecture-quiz-full'),

# Quiz Questions (nested under lecture quiz)
path('courses/<uuid:course_pk>/sections/<uuid:section_pk>/lectures/<uuid:lecture_pk>/quiz/questions/', 
     views.QuizQuestionViewSet.as_view({
         'get': 'list', 
         'post': 'create'
     }), 
     name='lecture-quiz-questions-list'),

path('courses/<uuid:course_pk>/sections/<uuid:section_pk>/lectures/<uuid:lecture_pk>/quiz/questions/<uuid:pk>/', 
     views.QuizQuestionViewSet.as_view({
         'get': 'retrieve', 
         'put': 'update', 
         'patch': 'partial_update', 
         'delete': 'destroy'
     }), 
     name='lecture-quiz-questions-detail'),

# Quiz Tasks (nested under lecture quiz)
path('courses/<uuid:course_pk>/sections/<uuid:section_pk>/lectures/<uuid:lecture_pk>/quiz/tasks/', 
     views.QuizTaskViewSet.as_view({
         'get': 'list', 
         'post': 'create'
     }), 
     name='lecture-quiz-tasks-list'),

path('courses/<uuid:course_pk>/sections/<uuid:section_pk>/lectures/<uuid:lecture_pk>/quiz/tasks/<uuid:pk>/', 
     views.QuizTaskViewSet.as_view({
         'get': 'retrieve', 
         'put': 'update', 
         'patch': 'partial_update', 
         'delete': 'destroy'
     }), 
     name='lecture-quiz-tasks-detail'),
path('courses/<uuid:course_pk>/sections/<uuid:section_pk>/lectures/<uuid:lecture_pk>/quiz/full/', 
     views.QuizViewSet.as_view({'get': 'retrieve_full'}), 
     name='lecture-quiz-full'),
]