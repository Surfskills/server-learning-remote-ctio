from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()

# Course related endpoints
router.register(r'courses', views.CourseViewSet)
router.register(r'course-categories', views.CourseCategoryViewSet)
router.register(r'courses/(?P<course_pk>[^/.]+)/sections', views.CourseSectionViewSet, basename='course-sections')
router.register(r'sections/(?P<section_pk>[^/.]+)/lectures', views.LectureViewSet, basename='section-lectures')
router.register(r'lectures/(?P<lecture_pk>[^/.]+)/resources', views.LectureResourceViewSet, basename='lecture-resources')
router.register(r'lectures/(?P<lecture_pk>[^/.]+)/qa', views.QaItemViewSet, basename='lecture-qa')
router.register(r'lectures/(?P<lecture_pk>[^/.]+)/project-tools', views.ProjectToolViewSet, basename='lecture-tools')
router.register(r'courses/(?P<course_pk>[^/.]+)/reviews', views.ReviewViewSet, basename='course-reviews')
router.register(r'courses/(?P<course_pk>[^/.]+)/quizzes', views.QuizViewSet, basename='course-quizzes')
router.register(r'quizzes/(?P<quiz_pk>[^/.]+)/questions', views.QuizQuestionViewSet, basename='quiz-questions')
router.register(r'quizzes/(?P<quiz_pk>[^/.]+)/tasks', views.QuizTaskViewSet, basename='quiz-tasks')
router.register(r'tasks/(?P<task_pk>[^/.]+)/criteria', views.GradingCriterionViewSet, basename='task-criteria')
router.register(r'quizzes/(?P<quiz_pk>[^/.]+)/submissions', views.QuizSubmissionViewSet, basename='quiz-submissions')
router.register(r'submissions/(?P<submission_pk>[^/.]+)/files', views.SubmissionFileViewSet, basename='submission-files')
router.register(r'quizzes/(?P<quiz_pk>[^/.]+)/grades', views.QuizGradeViewSet, basename='quiz-grades')
router.register(r'grades/(?P<grade_pk>[^/.]+)/task-grades', views.TaskGradeViewSet, basename='grade-tasks')
router.register(r'task-grades/(?P<task_grade_pk>[^/.]+)/criteria-grades', views.CriteriaGradeViewSet, basename='task-criteria-grades')
router.register(r'courses/(?P<course_pk>[^/.]+)/faqs', views.FaqViewSet, basename='course-faqs')
router.register(r'courses/(?P<course_pk>[^/.]+)/announcements', views.AnnouncementViewSet, basename='course-announcements')

# User related endpoints
router.register(r'enrollments', views.EnrollmentViewSet, basename='enrollments')
router.register(r'admin-enrollments', views.AdminEnrollmentViewSet, basename='admin-enrollments')
router.register(r'progress', views.CourseProgressViewSet, basename='progress')
router.register(r'orders', views.OrderViewSet, basename='orders')
router.register(r'certificates', views.CertificateViewSet, basename='certificates')
router.register(r'calendar-events', views.CalendarEventViewSet, basename='calendar-events')
router.register(r'calendar-notifications', views.CalendarNotificationViewSet, basename='calendar-notifications')
router.register(r'notification-preferences', views.NotificationPreferencesViewSet, basename='notification-preferences')
router.register(r'calendar-permissions', views.CalendarPermissionsViewSet, basename='calendar-permissions')
router.register(r'progress-controls', views.StudentProgressControlViewSet, basename='progress-controls')
router.register(r'planned-releases', views.PlannedCourseReleaseViewSet, basename='planned-releases')
router.register(r'drip-schedules', views.DripScheduleViewSet, basename='drip-schedules')
router.register(r'drip-schedule-entries', views.DripScheduleEntryViewSet, basename='drip-schedule-entries')

urlpatterns = [
    path('', include(router.urls)),
    
    # Course related views
    path('my-courses/', views.UserCoursesView.as_view(), name='user-courses'),
    path('search/', views.CourseSearchView.as_view(), name='course-search'),
    path('course-detail/<uuid:pk>/', views.CourseDetailView.as_view(), name='course-detail'),
    
    # Admin endpoints
    path('admin/stats/', views.admin_stats, name='admin-stats'),
    path('admin/course-analytics/', views.course_analytics, name='admin-course-analytics'),
    path('admin/user-analytics/', views.user_analytics, name='admin-user-analytics'),
    path('recent-enrollments/', views.recent_enrollments, name='recent-enrollments'),
    
    # Health check
    path('health/', views.health_check, name='health-check'),
]