from django.contrib import admin
from .models import Enrollment, CourseProgress

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'course', 'enrolled_at', 'completed', 'progress_percentage')
    list_filter = ('completed', 'course', 'enrolled_at')
    search_fields = ('student__email', 'course__title')
    raw_id_fields = ('student', 'course')
    readonly_fields = ('enrolled_at', 'last_accessed')

@admin.register(CourseProgress)
class CourseProgressAdmin(admin.ModelAdmin):
    list_display = ('enrollment', 'progress_percentage', 'last_accessed_lecture')
    list_filter = ('enrollment__course',)
    search_fields = ('enrollment__student__email', 'enrollment__course__title')
    raw_id_fields = ('enrollment', 'last_accessed_lecture')
    filter_horizontal = ('completed_lectures',)