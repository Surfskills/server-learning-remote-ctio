# admin.py
from django.contrib import admin
from .models import (
    CalendarEvent,
    CalendarNotification,
    CalendarPermissions,
    PlannedCourseRelease,
    StudentProgressControl,
    DripSchedule,
    DripScheduleEntry
)

@admin.register(CalendarEvent)
class CalendarEventAdmin(admin.ModelAdmin):
    list_display = ('title', 'event_type', 'course', 'start_time', 'status')
    list_filter = ('event_type', 'status', 'course')
    search_fields = ('title', 'description')
    filter_horizontal = ('attendees',)
    date_hierarchy = 'start_time'

@admin.register(CalendarNotification)
class CalendarNotificationAdmin(admin.ModelAdmin):
    list_display = ('event', 'user', 'type', 'scheduled_for', 'sent')
    list_filter = ('type', 'sent')
    search_fields = ('event__title', 'message')
    date_hierarchy = 'scheduled_for'



@admin.register(CalendarPermissions)
class CalendarPermissionsAdmin(admin.ModelAdmin):
    list_display = ('user', 'can_create_events', 'can_edit_events', 'can_delete_events')
    search_fields = ('user__email', 'user__first_name', 'user__last_name')

@admin.register(PlannedCourseRelease)
class PlannedCourseReleaseAdmin(admin.ModelAdmin):
    list_display = ('course', 'student', 'release_date', 'is_released')
    list_filter = ('is_released', 'course')
    search_fields = ('course__title', 'student__email')
    date_hierarchy = 'release_date'

@admin.register(StudentProgressControl)
class StudentProgressControlAdmin(admin.ModelAdmin):
    list_display = ('student', 'course', 'is_auto_release_enabled')
    search_fields = ('student__email', 'course__title')
    filter_horizontal = ('locked_lectures', 'unlocked_lectures')

@admin.register(DripSchedule)
class DripScheduleAdmin(admin.ModelAdmin):
    list_display = ('course', 'type')
    search_fields = ('course__title',)

@admin.register(DripScheduleEntry)
class DripScheduleEntryAdmin(admin.ModelAdmin):
    list_display = ('schedule', 'day_offset', 'release_date')
    list_filter = ('schedule__course', 'schedule__type')
    search_fields = ('schedule__course__title',)
    date_hierarchy = 'release_date'