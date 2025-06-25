from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'calendar-events', views.CalendarEventViewSet, basename='calendar-events')
router.register(r'calendar-notifications', views.CalendarNotificationViewSet, basename='calendar-notifications')
router.register(r'calendar-settings', views.UserCalendarSettingsViewSet, basename='calendar-settings')
router.register(r'release-schedules', views.ContentReleaseScheduleViewSet, basename='release-schedules')
router.register(r'release-rules', views.ContentReleaseRuleViewSet, basename='release-rules')
router.register(r'progress-overrides', views.StudentProgressOverrideViewSet, basename='progress-overrides')

urlpatterns = [
    path('', include(router.urls)),
    path('courses/<uuid:course_id>/events/', views.CourseEventsView.as_view(), name='course-events'),
]