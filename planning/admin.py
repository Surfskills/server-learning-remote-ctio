from django.contrib import admin
from .models import (
    CalendarEvent,
    CalendarNotification,
    UserCalendarSettings,
    ContentReleaseSchedule,
    ContentReleaseRule,
    StudentProgressOverride,
)


@admin.register(CalendarEvent)
class CalendarEventAdmin(admin.ModelAdmin):
    list_display = ('title', 'event_type', 'course_event_type', 'start_time', 'end_time', 'status', 'priority', 'created_by')
    list_filter = ('event_type', 'status', 'priority', 'is_recurring', 'course_event_type')
    search_fields = ('title', 'description', 'course__title', 'created_by__email')
    autocomplete_fields = ('course', 'section', 'lecture', 'attendees', 'created_by')
    date_hierarchy = 'start_time'
    ordering = ('start_time',)
    filter_horizontal = ('attendees',)


@admin.register(CalendarNotification)
class CalendarNotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'event', 'notification_type', 'delivery_method', 'scheduled_for', 'sent', 'sent_at')
    list_filter = ('notification_type', 'delivery_method', 'sent')
    search_fields = ('user__email', 'event__title', 'message')
    autocomplete_fields = ('user', 'event')


@admin.register(UserCalendarSettings)
class UserCalendarSettingsAdmin(admin.ModelAdmin):
    list_display = ('user', 'default_view', 'time_zone', 'working_hours_start', 'working_hours_end', 'color_scheme')
    search_fields = ('user__email',)
    autocomplete_fields = ('user',)


class ContentReleaseRuleInline(admin.TabularInline):
    model = ContentReleaseRule
    extra = 0
    autocomplete_fields = ('section', 'lecture', 'quiz', 'release_event')


@admin.register(ContentReleaseSchedule)
class ContentReleaseScheduleAdmin(admin.ModelAdmin):
    list_display = ('course', 'strategy', 'start_date', 'end_date', 'unlock_all', 'release_time')
    search_fields = ('course__title',)
    inlines = [ContentReleaseRuleInline]
    autocomplete_fields = ('course',)


@admin.register(ContentReleaseRule)
class ContentReleaseRuleAdmin(admin.ModelAdmin):
    list_display = ('schedule', 'trigger', 'offset_days', 'release_date', 'is_released')
    list_filter = ('trigger', 'is_released')
    search_fields = ('schedule__course__title',)
    autocomplete_fields = ('schedule', 'section', 'lecture', 'quiz', 'release_event')


@admin.register(StudentProgressOverride)
class StudentProgressOverrideAdmin(admin.ModelAdmin):
    list_display = ('student', 'rule', 'override_date', 'is_released')
    search_fields = ('student__email', 'rule__schedule__course__title')
    autocomplete_fields = ('student', 'rule')
