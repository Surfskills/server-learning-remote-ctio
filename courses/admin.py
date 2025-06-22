# admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Count, Avg

from .models import (
    CourseCategory, Course, CourseSection, Lecture, LectureResource,
    QaItem, ProjectTool, Quiz, QuizQuestion, QuizTask
)


@admin.register(CourseCategory)
class CourseCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'course_count', 'created_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at', 'updated_at']
    
    def course_count(self, obj):
        return obj.courses.count()
    course_count.short_description = 'Courses'
    course_count.admin_order_field = 'courses__count'
    
    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            course_count=Count('courses')
        )


class CourseSectionInline(admin.TabularInline):
    model = CourseSection
    extra = 1
    fields = ['title', 'order']
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
        'current_price_display', 'rating', 'students_enrolled', 
        'is_published', 'is_active', 'created_at'
    ]
    list_filter = [
        'is_published', 'is_active', 'level', 'language', 
        'category', 'created_at', 'published_at'
    ]
    search_fields = ['title', 'description', 'instructor__username', 'instructor__email']
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ['created_at', 'updated_at', 'published_at', 'thumbnail_preview']
    filter_horizontal = []
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'slug', 'description', 'long_description', 'instructor', 'category')
        }),
        ('Media', {
            'fields': ('thumbnail', 'thumbnail_preview', 'banner_url', 'preview_video_url'),
            'classes': ('collapse',)
        }),
        ('Course Details', {
            'fields': ('level', 'language', 'duration', 'price', 'discount_price')
        }),
        ('Statistics', {
            'fields': ('rating', 'review_count', 'students_enrolled'),
            'classes': ('collapse',)
        }),
        ('Publishing', {
            'fields': ('is_published', 'is_active', 'published_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    inlines = [CourseSectionInline, QuizInline]
    
    def current_price_display(self, obj):
        if obj.discount_price:
            return format_html(
                '<span style="text-decoration: line-through;">${}</span> <strong>${}</strong>',
                obj.price, obj.discount_price
            )
        return f'${obj.price}'
    current_price_display.short_description = 'Price'
    current_price_display.admin_order_field = 'price'
    
    def thumbnail_preview(self, obj):
        if obj.thumbnail:
            return format_html(
                '<img src="{}" width="100" height="60" style="object-fit: cover;" />',
                obj.thumbnail.url
            )
        elif obj.banner_url:
            return format_html(
                '<img src="{}" width="100" height="60" style="object-fit: cover;" />',
                obj.banner_url
            )
        return "No image"
    thumbnail_preview.short_description = 'Thumbnail Preview'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('instructor', 'category')


class LectureInline(admin.TabularInline):
    model = Lecture
    extra = 1
    fields = ['title', 'order', 'duration', 'preview_available']
    ordering = ['order']


@admin.register(CourseSection)
class CourseSectionAdmin(admin.ModelAdmin):
    list_display = ['title', 'course', 'order', 'lecture_count', 'created_at']
    list_filter = ['course', 'created_at']
    search_fields = ['title', 'course__title']
    
    inlines = [LectureInline]
    
    def lecture_count(self, obj):
        return obj.lectures.count()
    lecture_count.short_description = 'Lectures'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('course')


class LectureResourceInline(admin.TabularInline):
    model = LectureResource
    extra = 1
    fields = ['title', 'resource_type', 'provider', 'is_downloadable']


class QaItemInline(admin.TabularInline):
    model = QaItem
    extra = 0
    fields = ['question', 'answer', 'asked_by', 'upvotes', 'resolved']
    readonly_fields = ['asked_by', 'upvotes']


class ProjectToolInline(admin.TabularInline):
    model = ProjectTool
    extra = 1
    fields = ['name', 'description', 'url', 'icon']


class QuizInlineForLecture(admin.TabularInline):
    model = Quiz
    extra = 0
    fields = ['title', 'points_possible', 'is_published']
    fk_name = 'lecture'


@admin.register(Lecture)
class LectureAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'section', 'course_title', 'order', 'duration', 
        'preview_available', 'resource_count', 'created_at'
    ]
    list_filter = ['preview_available', 'section__course', 'created_at']
    search_fields = ['title', 'overview', 'section__title', 'section__course__title']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('section', 'title', 'order', 'duration', 'overview')
        }),
        ('Media', {
            'fields': ('video_url', 'preview_available')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = ['created_at', 'updated_at']
    inlines = [LectureResourceInline, QaItemInline, ProjectToolInline, QuizInlineForLecture]
    
    def course_title(self, obj):
        return obj.section.course.title
    course_title.short_description = 'Course'
    course_title.admin_order_field = 'section__course__title'
    
    def resource_count(self, obj):
        return obj.resources.count()
    resource_count.short_description = 'Resources'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('section__course')


@admin.register(LectureResource)
class LectureResourceAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'lecture', 'resource_type', 'provider', 
        'is_downloadable', 'file_size_display', 'created_at'
    ]
    list_filter = ['resource_type', 'provider', 'is_downloadable', 'created_at']
    search_fields = ['title', 'description', 'lecture__title']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('lecture', 'title', 'description', 'resource_type', 'provider')
        }),
        ('URLs and Files', {
            'fields': ('url', 'file_url', 'external_url', 'file')
        }),
        ('Properties', {
            'fields': ('duration_seconds', 'is_downloadable', 'file_size', 'mime_type')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    def file_size_display(self, obj):
        if obj.file_size:
            if obj.file_size < 1024:
                return f'{obj.file_size} B'
            elif obj.file_size < 1024 * 1024:
                return f'{obj.file_size / 1024:.1f} KB'
            else:
                return f'{obj.file_size / (1024 * 1024):.1f} MB'
        return '-'
    file_size_display.short_description = 'File Size'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('lecture__section__course')


@admin.register(QaItem)
class QaItemAdmin(admin.ModelAdmin):
    list_display = [
        'question_preview', 'lecture', 'asked_by', 'upvotes', 
        'resolved', 'created_at'
    ]
    list_filter = ['resolved', 'created_at', 'lecture__section__course']
    search_fields = ['question', 'answer', 'asked_by__username']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Question', {
            'fields': ('lecture', 'question', 'asked_by')
        }),
        ('Answer', {
            'fields': ('answer', 'resolved')
        }),
        ('Engagement', {
            'fields': ('upvotes',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def question_preview(self, obj):
        return obj.question[:100] + '...' if len(obj.question) > 100 else obj.question
    question_preview.short_description = 'Question'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('lecture', 'asked_by')


@admin.register(ProjectTool)
class ProjectToolAdmin(admin.ModelAdmin):
    list_display = ['name', 'lecture', 'url', 'created_at']
    list_filter = ['created_at', 'lecture__section__course']
    search_fields = ['name', 'description', 'lecture__title']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('lecture__section__course')


class QuizQuestionInline(admin.TabularInline):
    model = QuizQuestion
    extra = 1
    fields = ['question', 'question_type', 'points', 'order']
    ordering = ['order']


class QuizTaskInline(admin.TabularInline):
    model = QuizTask
    extra = 1
    fields = ['title', 'points', 'accepts_files', 'accepts_text', 'required', 'order']
    ordering = ['order']


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'course', 'lecture', 'section', 'points_possible', 
        'is_published', 'due_date', 'question_count', 'created_at'
    ]
    list_filter = [
        'is_published', 'allow_multiple_attempts', 'course', 'created_at'
    ]
    search_fields = ['title', 'description', 'course__title']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'instructions', 'course', 'section', 'lecture')
        }),
        ('Scoring', {
            'fields': ('points_possible', 'due_date')
        }),
        ('Settings', {
            'fields': ('is_published', 'allow_multiple_attempts', 'max_attempts', 'time_limit_minutes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = ['created_at', 'updated_at']
    inlines = [QuizQuestionInline, QuizTaskInline]
    
    def question_count(self, obj):
        return obj.questions.count()
    question_count.short_description = 'Questions'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('course', 'lecture', 'section')


@admin.register(QuizQuestion)
class QuizQuestionAdmin(admin.ModelAdmin):
    list_display = [
        'question_preview', 'quiz', 'question_type', 'points', 'order'
    ]
    list_filter = ['question_type', 'quiz__course', 'created_at']
    search_fields = ['question', 'quiz__title']
    
    fieldsets = (
        ('Question', {
            'fields': ('quiz', 'question', 'question_type', 'order')
        }),
        ('Answer Options', {
            'fields': ('options', 'correct_option_index', 'correct_answer')
        }),
        ('Scoring', {
            'fields': ('points', 'explanation')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    def question_preview(self, obj):
        return obj.question[:100] + '...' if len(obj.question) > 100 else obj.question
    question_preview.short_description = 'Question'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('quiz__course')


@admin.register(QuizTask)
class QuizTaskAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'quiz', 'points', 'accepts_files', 'accepts_text', 
        'required', 'order'
    ]
    list_filter = ['accepts_files', 'accepts_text', 'required', 'quiz__course']
    search_fields = ['title', 'description', 'quiz__title']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('quiz', 'title', 'description', 'order')
        }),
        ('Submission Settings', {
            'fields': ('accepts_files', 'accepts_text', 'accepted_file_types', 'max_file_size', 'max_files')
        }),
        ('Scoring', {
            'fields': ('points', 'required', 'sample_answer')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('quiz__course')


# Custom admin site configuration
admin.site.site_header = "Course Management System"
admin.site.site_title = "CMS Admin"
admin.site.index_title = "Welcome to Course Management System"