from django.contrib import admin
from enrollments.models import Enrollment, CourseProgress

class CourseProgressInline(admin.StackedInline):
    model = CourseProgress
    extra = 0
    readonly_fields = ('created_at', 'updated_at')
    filter_horizontal = ('completed_lectures',)
    fieldsets = (
        (None, {
            'fields': ('enrollment', 'last_accessed_lecture', 'completed_lectures')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'course', 'enrolled_at', 'progress_percentage', 'completed', 'last_accessed')
    list_filter = ('completed', 'course', 'enrolled_at')
    search_fields = ('student__email', 'course__title')
    readonly_fields = ('enrolled_at', 'last_accessed', 'created_at', 'updated_at')
    date_hierarchy = 'enrolled_at'
    inlines = [CourseProgressInline]
    
    fieldsets = (
        (None, {
            'fields': ('student', 'course', 'progress_percentage', 'completed')
        }),
        ('Timestamps', {
            'fields': ('enrolled_at', 'last_accessed', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(CourseProgress)
class CourseProgressAdmin(admin.ModelAdmin):
    list_display = ('enrollment', 'progress_percentage', 'last_accessed_lecture')
    list_select_related = ('enrollment', 'last_accessed_lecture')
    search_fields = ('enrollment__student__email', 'enrollment__course__title')
    readonly_fields = ('created_at', 'updated_at')
    filter_horizontal = ('completed_lectures',)
    
    fieldsets = (
        (None, {
            'fields': ('enrollment', 'last_accessed_lecture', 'completed_lectures')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def progress_percentage(self, obj):
        return f"{obj.enrollment.progress_percentage}%"
    progress_percentage.short_description = 'Progress'