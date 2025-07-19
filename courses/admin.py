# admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count
from django.utils.safestring import mark_safe
from .models import (
    CourseCategory, Course, CourseSection, Lecture, LectureResource,
    QaItem, ProjectTool, Quiz, QuizQuestion, QuizTask
)


@admin.register(CourseCategory)
class CourseCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'course_count', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at', 'updated_at']
    
    def course_count(self, obj):
        return obj.courses.count()
    course_count.short_description = 'Courses'
    
    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            course_count=Count('courses')
        )


class CourseSectionInline(admin.TabularInline):
    model = CourseSection
    extra = 0
    fields = ['title', 'order', 'description']
    ordering = ['order']


class QuizInline(admin.TabularInline):
    model = Quiz
    extra = 0
    fields = ['title', 'points_possible', 'is_published', 'due_date']
    readonly_fields = ['created_at']


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'instructor', 'category', 'level', 'language', 
        'current_price', 'students_enrolled', 'rating', 'is_published', 
        'is_active', 'published_at'
    ]
    list_filter = [
        'is_published', 'is_active', 'level', 'language', 'category',
        'certificate_available', 'lifetime_access', 'created_at'
    ]
    search_fields = ['title', 'description', 'instructor__username', 'instructor__email']
    
    # Remove slug from prepopulated_fields since it's auto-generated
    # prepopulated_fields = {'slug': ('title',)}  # REMOVE THIS LINE
    
    readonly_fields = ['slug', 'students_enrolled', 'review_count', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'slug', 'instructor', 'category', 'level', 'language')
        }),
        ('Content', {
            'fields': ('description', 'long_description', 'what_you_will_learn', 'who_is_this_for')
        }),
        ('Media', {
            'fields': ('banner_url', 'thumbnail', 'preview_video_url'),
            'classes': ('collapse',)
        }),
        ('Pricing', {
            'fields': ('price', 'discount_price'),
            'classes': ('collapse',)
        }),
        ('Settings', {
            'fields': (
                'duration', 'prerequisites', 'certificate_available', 
                'lifetime_access', 'is_published', 'is_active'
            )
        }),
        ('Statistics', {
            'fields': ('rating', 'review_count', 'students_enrolled'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('published_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    inlines = [CourseSectionInline, QuizInline]
    
    filter_horizontal = ['prerequisites']
    
    def current_price(self, obj):
        price = obj.current_price
        if obj.discount_price and obj.discount_price < obj.price:
            return format_html(
                '<span style="text-decoration: line-through;">${}</span> <strong>${}</strong>',
                obj.price, obj.discount_price
            )
        return f'${price}'
    current_price.short_description = 'Price'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'instructor', 'category'
        ).prefetch_related('prerequisites')
    
    actions = ['publish_courses', 'unpublish_courses', 'activate_courses', 'deactivate_courses']
    
    def publish_courses(self, request, queryset):
        updated = queryset.update(is_published=True)
        self.message_user(request, f'{updated} courses were published.')
    publish_courses.short_description = 'Publish selected courses'
    
    def unpublish_courses(self, request, queryset):
        updated = queryset.update(is_published=False)
        self.message_user(request, f'{updated} courses were unpublished.')
    unpublish_courses.short_description = 'Unpublish selected courses'
    
    def activate_courses(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} courses were activated.')
    activate_courses.short_description = 'Activate selected courses'
    
    def deactivate_courses(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} courses were deactivated.')
    deactivate_courses.short_description = 'Deactivate selected courses'

class LectureInline(admin.TabularInline):
    model = Lecture
    extra = 0
    fields = ['title', 'order', 'duration', 'preview_available']
    ordering = ['order']


@admin.register(CourseSection)
class CourseSectionAdmin(admin.ModelAdmin):
    list_display = ['title', 'course', 'order', 'lecture_count', 'created_at']
    list_filter = ['course', 'created_at']
    search_fields = ['title', 'description', 'course__title']
    readonly_fields = ['created_at', 'updated_at']
    
    inlines = [LectureInline]
    
    def lecture_count(self, obj):
        return obj.lectures.count()
    lecture_count.short_description = 'Lectures'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('course')


class LectureResourceInline(admin.TabularInline):
    model = LectureResource
    extra = 0
    fields = ['title', 'resource_type', 'url', 'is_downloadable']


class QaItemInline(admin.TabularInline):
    model = QaItem
    extra = 0
    fields = ['question', 'answer', 'asked_by', 'upvotes', 'resolved']
    readonly_fields = ['asked_by', 'upvotes']


class ProjectToolInline(admin.TabularInline):
    model = ProjectTool
    extra = 0
    fields = ['name', 'url', 'icon']


class QuizInlineForLecture(admin.TabularInline):
    model = Quiz
    extra = 0
    fields = ['title', 'points_possible', 'is_published']
    fk_name = 'lecture'


@admin.register(Lecture)
class LectureAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'section', 'get_course', 'order', 'duration', 
        'preview_available', 'resource_count', 'created_at'
    ]
    list_filter = ['preview_available', 'section__course', 'created_at']
    search_fields = ['title', 'overview', 'section__title', 'section__course__title']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('section', 'title', 'order', 'duration')
        }),
        ('Content', {
            'fields': ('overview', 'video_url', 'preview_available')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    inlines = [LectureResourceInline, QaItemInline, ProjectToolInline, QuizInlineForLecture]
    
    def get_course(self, obj):
        return obj.section.course.title
    get_course.short_description = 'Course'
    get_course.admin_order_field = 'section__course__title'
    
    def resource_count(self, obj):
        return obj.resources.count()
    resource_count.short_description = 'Resources'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'section', 'section__course'
        ).prefetch_related('resources')


@admin.register(LectureResource)
class LectureResourceAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'lecture', 'resource_type', 'provider', 
        'is_downloadable', 'file_size_display', 'created_at'
    ]
    list_filter = ['resource_type', 'provider', 'is_downloadable', 'created_at']
    search_fields = ['title', 'description', 'lecture__title']
    readonly_fields = ['created_at', 'updated_at', 'effective_url']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('lecture', 'title', 'description', 'resource_type')
        }),
        ('Content', {
            'fields': ('url', 'file_url', 'external_url', 'file', 'effective_url')
        }),
        ('Settings', {
            'fields': ('provider', 'is_downloadable', 'duration_seconds')
        }),
        ('File Information', {
            'fields': ('file_size', 'mime_type'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def file_size_display(self, obj):
        if obj.file_size:
            # Convert bytes to readable format
            for unit in ['B', 'KB', 'MB', 'GB']:
                if obj.file_size < 1024.0:
                    return f"{obj.file_size:.1f} {unit}"
                obj.file_size /= 1024.0
            return f"{obj.file_size:.1f} TB"
        return '-'
    file_size_display.short_description = 'File Size'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('lecture')


@admin.register(QaItem)
class QaItemAdmin(admin.ModelAdmin):
    list_display = [
        'question_preview', 'lecture', 'asked_by', 'upvotes', 
        'resolved', 'created_at'
    ]
    list_filter = ['resolved', 'created_at']
    search_fields = ['question', 'answer', 'lecture__title']
    readonly_fields = ['created_at', 'updated_at']
    
    def question_preview(self, obj):
        return obj.question[:50] + '...' if len(obj.question) > 50 else obj.question
    question_preview.short_description = 'Question'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('lecture', 'asked_by')


@admin.register(ProjectTool)
class ProjectToolAdmin(admin.ModelAdmin):
    list_display = ['name', 'lecture', 'url', 'icon', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'description', 'lecture__title']
    readonly_fields = ['created_at', 'updated_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('lecture')


class QuizQuestionInline(admin.TabularInline):
    model = QuizQuestion
    extra = 0
    fields = ['question', 'question_type', 'points', 'order']
    ordering = ['order']


class QuizTaskInline(admin.TabularInline):
    model = QuizTask
    extra = 0
    fields = ['title', 'points', 'accepts_files', 'accepts_text', 'required', 'order']
    ordering = ['order']


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'course', 'get_location', 'points_possible', 
        'is_published', 'question_count', 'due_date', 'created_at'
    ]
    list_filter = [
        'is_published', 'allow_multiple_attempts', 'course', 'created_at'
    ]
    search_fields = ['title', 'description', 'course__title']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'course', 'lecture', 'section', 'description')
        }),
        ('Instructions', {
            'fields': ('instructions', 'points_possible', 'due_date')
        }),
        ('Settings', {
            'fields': (
                'is_published', 'allow_multiple_attempts', 'max_attempts', 
                'time_limit_minutes'
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    inlines = [QuizQuestionInline, QuizTaskInline]
    
    def get_location(self, obj):
        if obj.lecture:
            return f"Lecture: {obj.lecture.title}"
        elif obj.section:
            return f"Section: {obj.section.title}"
        return "Course Level"
    get_location.short_description = 'Location'
    
    def question_count(self, obj):
        return obj.questions.count()
    question_count.short_description = 'Questions'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'course', 'lecture', 'section'
        ).prefetch_related('questions')


@admin.register(QuizQuestion)
class QuizQuestionAdmin(admin.ModelAdmin):
    list_display = [
        'question_preview', 'quiz', 'question_type', 'points', 
        'order', 'created_at'
    ]
    list_filter = ['question_type', 'quiz__course', 'created_at']
    search_fields = ['question', 'quiz__title']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('quiz', 'question', 'question_type', 'points', 'order')
        }),
        ('Answer Settings', {
            'fields': ('options', 'correct_option_index', 'correct_answer', 'explanation')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def question_preview(self, obj):
        return obj.question[:50] + '...' if len(obj.question) > 50 else obj.question
    question_preview.short_description = 'Question'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('quiz')


@admin.register(QuizTask)
class QuizTaskAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'quiz', 'points', 'accepts_files', 'accepts_text', 
        'required', 'order', 'created_at'
    ]
    list_filter = ['accepts_files', 'accepts_text', 'required', 'quiz__course', 'created_at']
    search_fields = ['title', 'description', 'quiz__title']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('quiz', 'title', 'description', 'points', 'order')
        }),
        ('Submission Settings', {
            'fields': (
                'accepts_files', 'accepts_text', 'accepted_file_types', 
                'max_file_size', 'max_files', 'required'
            )
        }),
        ('Sample Answer', {
            'fields': ('sample_answer',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('quiz')


# Admin site customization
admin.site.site_header = 'Course Management System'
admin.site.site_title = 'Course Admin'
admin.site.index_title = 'Welcome to Course Administration'