# urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'calendar-events', views.CalendarEventViewSet, basename='calendar-events')
router.register(r'calendar-notifications', views.CalendarNotificationViewSet, basename='calendar-notifications')
router.register(r'calendar-permissions', views.CalendarPermissionsViewSet, basename='calendar-permissions')
router.register(r'progress-controls', views.StudentProgressControlViewSet, basename='progress-controls')
router.register(r'planned-releases', views.PlannedCourseReleaseViewSet, basename='planned-releases')
router.register(r'drip-schedules', views.DripScheduleViewSet, basename='drip-schedules')
router.register(r'drip-schedule-entries', views.DripScheduleEntryViewSet, basename='drip-schedule-entries')

urlpatterns = [
    path('', include(router.urls)),
    path('upcoming-events/', views.UpcomingEventsView.as_view(), name='upcoming-events'),
    path('user-events/', views.UserEventsView.as_view(), name='user-events'),
]