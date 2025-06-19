from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Count, Q
from django.utils import timezone

from .models import CourseCategory, Course, CourseSection, Lecture, LectureResource


@admin.register(CourseCategory)
class CourseCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'course_count', 'created_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'description')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def course_count(self, obj):
        count = obj.courses.count()
        if count > 0:
            url = reverse('admin:courses_course_changelist') + f'?category__id={obj.id}'
            return format_html('<a href="{}">{} courses</a>', url, count)
        return '0 courses'
    course_count.short_description = 'Courses'


class LectureResourceInline(admin.TabularInline):
    model = LectureResource
    extra = 1
    fields = ['title', 'resource_type', 'url', 'file', 'is_downloadable', 'provider']
    readonly_fields = []


class LectureInline(admin.TabularInline):
    model = Lecture
    extra = 1
    fields = ['title', 'order', 'duration', 'preview_available']
    ordering = ['order']


class CourseSectionInline(admin.TabularInline):
    model = CourseSection
    extra = 1
    fields = ['title', 'order']
    ordering = ['order']


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'instructor', 'category', 'level', 'current_price_display', 
        'students_enrolled', 'rating_display', 'is_published', 'is_active', 'published_at'
    ]
    list_filter = [
        'is_published', 'is_active', 'level', 'language', 'category', 
        'created_at', 'published_at', 'instructor'
    ]
    search_fields = ['title', 'description', 'instructor__first_name', 'instructor__last_name']
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ['created_at', 'updated_at', 'rating', 'review_count', 'students_enrolled']
    list_editable = ['is_published', 'is_active']
    list_per_page = 25
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'slug', 'instructor', 'category')
        }),
        ('Content', {
            'fields': ('description', 'long_description', 'level', 'language', 'duration')
        }),
        ('Media', {
            'fields': ('thumbnail', 'banner_url', 'preview_video_url'),
            'classes': ('collapse',)
        }),
        ('Pricing', {
            'fields': ('price', 'discount_price'),
        }),
        ('Statistics', {
            'fields': ('rating', 'review_count', 'students_enrolled'),
            'classes': ('collapse',)
        }),
        ('Publication', {
            'fields': ('is_published', 'is_active', 'published_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [CourseSectionInline]
    
    actions = ['publish_courses', 'unpublish_courses', 'activate_courses', 'deactivate_courses']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'instructor', 'category'
        ).annotate(
            section_count=Count('sections'),
            lecture_count=Count('sections__lectures')
        )
    
    def current_price_display(self, obj):
        if obj.discount_price:
            return format_html(
                '<span style="text-decoration: line-through; color: #999;">${}</span> '
                '<strong style="color: #e74c3c;">${}</strong>',
                obj.price, obj.discount_price
            )
        return f'${obj.price}'
    current_price_display.short_description = 'Price'
    
    def rating_display(self, obj):
        if obj.rating > 0:
            stars = '★' * int(obj.rating) + '☆' * (5 - int(obj.rating))
            return format_html(
                '<span title="{} stars ({} reviews)">{} {:.1f}</span>',
                obj.rating, obj.review_count, stars, obj.rating
            )
        return 'No ratings'
    rating_display.short_description = 'Rating'
    
    def status_display(self, obj):
        if not obj.is_active:
            return format_html('<span style="color: #999;">Archived</span>')
        elif obj.is_published:
            return format_html('<span style="color: #27ae60;">Published</span>')
        else:
            return format_html('<span style="color: #f39c12;">Draft</span>')
    status_display.short_description = 'Status'
    
    def publish_courses(self, request, queryset):
        updated = queryset.update(is_published=True, published_at=timezone.now())
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


@admin.register(CourseSection)
class CourseSectionAdmin(admin.ModelAdmin):
    list_display = ['title', 'course', 'order', 'lecture_count', 'created_at']
    list_filter = ['course', 'created_at']
    search_fields = ['title', 'course__title']
    list_editable = ['order']
    ordering = ['course', 'order']
    
    fieldsets = (
        ('Section Information', {
            'fields': ('course', 'title', 'order')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    inlines = [LectureInline]
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('course').annotate(
            lecture_count=Count('lectures')
        )
    
    def lecture_count(self, obj):
        count = obj.lecture_count
        if count > 0:
            url = reverse('admin:courses_lecture_changelist') + f'?section__id={obj.id}'
            return format_html('<a href="{}">{} lectures</a>', url, count)
        return '0 lectures'
    lecture_count.short_description = 'Lectures'


@admin.register(Lecture)
class LectureAdmin(admin.ModelAdmin):
    list_display = ['title', 'section', 'course_title', 'order', 'duration', 'preview_available', 'resource_count']
    list_filter = ['preview_available', 'section__course', 'created_at']
    search_fields = ['title', 'overview', 'section__title', 'section__course__title']
    list_editable = ['order', 'preview_available']
    ordering = ['section__course', 'section__order', 'order']
    
    fieldsets = (
        ('Lecture Information', {
            'fields': ('section', 'title', 'order', 'duration')
        }),
        ('Content', {
            'fields': ('overview', 'video_url', 'preview_available')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    inlines = [LectureResourceInline]
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'section', 'section__course'
        ).annotate(
            resource_count=Count('resources')
        )
    
    def course_title(self, obj):
        return obj.section.course.title
    course_title.short_description = 'Course'
    
    def resource_count(self, obj):
        count = obj.resource_count
        if count > 0:
            url = reverse('admin:courses_lectureresource_changelist') + f'?lecture__id={obj.id}'
            return format_html('<a href="{}">{} resources</a>', url, count)
        return '0 resources'
    resource_count.short_description = 'Resources'


@admin.register(LectureResource)
class LectureResourceAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'lecture', 'resource_type', 'provider', 'file_size_display', 
        'is_downloadable', 'has_file', 'created_at'
    ]
    list_filter = [
        'resource_type', 'provider', 'is_downloadable', 'lecture__section__course', 'created_at'
    ]
    search_fields = ['title', 'description', 'lecture__title']
    list_editable = ['is_downloadable']
    
    fieldsets = (
        ('Resource Information', {
            'fields': ('lecture', 'title', 'description', 'resource_type')
        }),
        ('Source', {
            'fields': ('provider', 'url', 'file_url', 'external_url', 'file')
        }),
        ('Properties', {
            'fields': ('is_downloadable', 'duration_seconds', 'file_size', 'mime_type'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at', 'effective_url_display']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'lecture', 'lecture__section', 'lecture__section__course'
        )
    
    def file_size_display(self, obj):
        if obj.file_size:
            # Convert bytes to human readable format
            for unit in ['B', 'KB', 'MB', 'GB']:
                if obj.file_size < 1024:
                    return f"{obj.file_size:.1f} {unit}"
                obj.file_size /= 1024
            return f"{obj.file_size:.1f} TB"
        return '-'
    file_size_display.short_description = 'File Size'
    
    def has_file(self, obj):
        return bool(obj.file)
    has_file.boolean = True
    has_file.short_description = 'Has File'
    
    def effective_url_display(self, obj):
        url = obj.effective_url
        if url:
            return format_html('<a href="{}" target="_blank">{}</a>', url, url[:50] + '...' if len(url) > 50 else url)
        return 'No URL'
    effective_url_display.short_description = 'Effective URL'


# Customize admin site header and title
admin.site.site_header = 'Course Management Admin'
admin.site.site_title = 'Course Admin'
admin.site.index_title = 'Welcome to Course Management'