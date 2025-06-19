from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import *


class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'first_name', 'last_name', 'user_type', 'is_staff', 'is_active')
    list_filter = ('user_type', 'is_staff', 'is_active')
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'profile_picture')}),
        ('Permissions', {'fields': ('user_type', 'is_staff', 'is_active', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'user_type', 'is_staff', 'is_active'),
        }),
    )
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('email',)
    filter_horizontal = ('groups', 'user_permissions',)



class CourseCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}

admin.site.register(CourseCategory, CourseCategoryAdmin)

class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'instructor', 'category', 'price', 'is_published', 'created_at')
    list_filter = ('category', 'is_published', 'level', 'language')
    search_fields = ('title', 'description', 'instructor__email')
    prepopulated_fields = {'slug': ('title',)}
    raw_id_fields = ('instructor', 'category')

admin.site.register(Course, CourseAdmin)

class CourseSectionAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'order')
    list_filter = ('course',)
    search_fields = ('title', 'course__title')
    ordering = ('course', 'order')

admin.site.register(CourseSection, CourseSectionAdmin)

class LectureAdmin(admin.ModelAdmin):
    list_display = ('title', 'section', 'order', 'preview_available')
    list_filter = ('section__course', 'preview_available')
    search_fields = ('title', 'section__title')
    ordering = ('section', 'order')

admin.site.register(Lecture, LectureAdmin)

class LectureResourceAdmin(admin.ModelAdmin):
    list_display = ('title', 'lecture', 'kind', 'is_downloadable')
    list_filter = ('kind', 'is_downloadable', 'provider')
    search_fields = ('title', 'lecture__title')

admin.site.register(LectureResource, LectureResourceAdmin)

class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'course', 'enrolled_at', 'progress_percentage', 'completed')
    list_filter = ('course', 'completed')
    search_fields = ('student__email', 'course__title')
    raw_id_fields = ('student', 'course')

admin.site.register(Enrollment, EnrollmentAdmin)

class CourseProgressAdmin(admin.ModelAdmin):
    list_display = ('enrollment', 'progress_percentage')
    search_fields = ('enrollment__student__email', 'enrollment__course__title')
    raw_id_fields = ('enrollment', 'last_accessed_lecture')
    filter_horizontal = ('completed_lectures',)

admin.site.register(CourseProgress, CourseProgressAdmin)

class ReviewAdmin(admin.ModelAdmin):
    list_display = ('course', 'student', 'rating', 'created_at')
    list_filter = ('course', 'rating')
    search_fields = ('course__title', 'student__email', 'comment')
    raw_id_fields = ('course', 'student')

admin.site.register(Review, ReviewAdmin)

class QuizAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'due_date', 'points_possible')
    list_filter = ('course',)
    search_fields = ('title', 'course__title', 'description')
    raw_id_fields = ('course', 'section', 'lecture')

admin.site.register(Quiz, QuizAdmin)

class QuizQuestionAdmin(admin.ModelAdmin):
    list_display = ('quiz', 'question')
    search_fields = ('question', 'quiz__title')
    raw_id_fields = ('quiz',)

admin.site.register(QuizQuestion, QuizQuestionAdmin)

class QuizTaskAdmin(admin.ModelAdmin):
    list_display = ('quiz', 'question', 'points')
    search_fields = ('question', 'quiz__title')
    raw_id_fields = ('quiz',)

admin.site.register(QuizTask, QuizTaskAdmin)

class GradingCriterionAdmin(admin.ModelAdmin):
    list_display = ('task', 'description', 'points')
    search_fields = ('description', 'task__question')
    raw_id_fields = ('task',)

admin.site.register(GradingCriterion, GradingCriterionAdmin)

class QuizSubmissionAdmin(admin.ModelAdmin):
    list_display = ('quiz', 'student', 'submitted_at', 'status', 'grade')
    list_filter = ('status', 'quiz__course')
    search_fields = ('quiz__title', 'student__email')
    raw_id_fields = ('quiz', 'student')

admin.site.register(QuizSubmission, QuizSubmissionAdmin)

class SubmissionFileAdmin(admin.ModelAdmin):
    list_display = ('submission', 'name', 'type', 'size')
    list_filter = ('type',)
    search_fields = ('name', 'submission__quiz__title')
    raw_id_fields = ('submission',)

admin.site.register(SubmissionFile, SubmissionFileAdmin)

class QuizGradeAdmin(admin.ModelAdmin):
    list_display = ('quiz', 'student', 'overall_score', 'graded_at')
    search_fields = ('quiz__title', 'student__email')
    raw_id_fields = ('quiz', 'student', 'graded_by')

admin.site.register(QuizGrade, QuizGradeAdmin)

class TaskGradeAdmin(admin.ModelAdmin):
    list_display = ('grade', 'task', 'score')
    search_fields = ('grade__quiz__title', 'task__question')
    raw_id_fields = ('grade', 'task')

admin.site.register(TaskGrade, TaskGradeAdmin)

class CriteriaGradeAdmin(admin.ModelAdmin):
    list_display = ('task_grade', 'criterion', 'awarded_points')
    search_fields = ('criterion__description', 'task_grade__grade__quiz__title')
    raw_id_fields = ('task_grade', 'criterion')

admin.site.register(CriteriaGrade, CriteriaGradeAdmin)

class OrderAdmin(admin.ModelAdmin):
    list_display = ('user', 'course', 'amount', 'payment_method', 'status', 'purchased_at')
    list_filter = ('payment_method', 'status')
    search_fields = ('user__email', 'course__title')
    raw_id_fields = ('user', 'course')

admin.site.register(Order, OrderAdmin)

class CertificateAdmin(admin.ModelAdmin):
    list_display = ('student', 'course', 'issued_at')
    search_fields = ('student__email', 'course__title')
    raw_id_fields = ('student', 'course')

admin.site.register(Certificate, CertificateAdmin)

class FaqAdmin(admin.ModelAdmin):
    list_display = ('course', 'question')
    search_fields = ('question', 'answer', 'course__title')
    raw_id_fields = ('course',)

admin.site.register(Faq, FaqAdmin)

class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('course', 'title', 'published_at')
    search_fields = ('title', 'content', 'course__title')
    raw_id_fields = ('course',)

admin.site.register(Announcement, AnnouncementAdmin)

class CalendarEventAdmin(admin.ModelAdmin):
    list_display = ('title', 'event_type', 'course', 'start_time', 'status')
    list_filter = ('event_type', 'status', 'priority', 'course')
    search_fields = ('title', 'description', 'course__title')
    raw_id_fields = ('course', 'related_lecture', 'created_by')
    filter_horizontal = ('attendees',)

admin.site.register(CalendarEvent, CalendarEventAdmin)

class CalendarNotificationAdmin(admin.ModelAdmin):
    list_display = ('event', 'user', 'type', 'scheduled_for', 'sent')
    list_filter = ('type', 'sent')
    search_fields = ('event__title', 'user__email')
    raw_id_fields = ('event', 'user')

admin.site.register(CalendarNotification, CalendarNotificationAdmin)

class NotificationPreferencesAdmin(admin.ModelAdmin):
    list_display = ('user', 'email_notifications', 'push_notifications')
    search_fields = ('user__email',)
    raw_id_fields = ('user',)

admin.site.register(NotificationPreferences, NotificationPreferencesAdmin)

class CalendarPermissionsAdmin(admin.ModelAdmin):
    list_display = ('user', 'can_create_events', 'can_edit_events', 'can_delete_events')
    search_fields = ('user__email',)
    raw_id_fields = ('user',)

admin.site.register(CalendarPermissions, CalendarPermissionsAdmin)

class PlannedCourseReleaseAdmin(admin.ModelAdmin):
    list_display = ('course', 'student', 'release_date', 'is_released')
    list_filter = ('is_released', 'course')
    search_fields = ('course__title', 'student__email')
    raw_id_fields = ('course', 'student', 'section', 'lecture', 'related_event')

admin.site.register(PlannedCourseRelease, PlannedCourseReleaseAdmin)

class StudentProgressControlAdmin(admin.ModelAdmin):
    list_display = ('student', 'course', 'is_auto_release_enabled')
    search_fields = ('student__email', 'course__title')
    raw_id_fields = ('student', 'course')
    filter_horizontal = ('locked_lectures', 'unlocked_lectures',)

admin.site.register(StudentProgressControl, StudentProgressControlAdmin)

class DripScheduleAdmin(admin.ModelAdmin):
    list_display = ('course', 'type')
    list_filter = ('type',)
    search_fields = ('course__title',)
    raw_id_fields = ('course',)

admin.site.register(DripSchedule, DripScheduleAdmin)

class DripScheduleEntryAdmin(admin.ModelAdmin):
    list_display = ('schedule', 'day_offset', 'release_date')
    search_fields = ('schedule__course__title',)
    raw_id_fields = ('schedule', 'section', 'lecture')

admin.site.register(DripScheduleEntry, DripScheduleEntryAdmin)