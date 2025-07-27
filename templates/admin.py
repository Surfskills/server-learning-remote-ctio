from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Count, Q
from django.utils import timezone

from ebooks.models import Chapter, EbookCollaborator, EbookExport, EbookProject
from .models import (

    EbookTemplate, UserTemplate
)

# Unregister models if they're already registered
models_to_unregister = [EbookProject, EbookCollaborator, Chapter, EbookExport]
for model in models_to_unregister:
    try:
        admin.site.unregister(model)
    except admin.sites.NotRegistered:
        pass


class ChapterInline(admin.TabularInline):
    model = Chapter
    fields = ('order', 'title', 'is_draft', 'updated_at')
    readonly_fields = ('updated_at',)
    extra = 0
    ordering = ['order']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('ebook')


class EbookCollaboratorInline(admin.TabularInline):
    model = EbookCollaborator
    fields = ('user', 'role', 'can_edit', 'can_export', 'joined_at')
    readonly_fields = ('joined_at',)
    extra = 0
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'ebook')


class EbookExportInline(admin.TabularInline):
    model = EbookExport
    fields = ('format', 'version', 'file_size_display', 'download_count', 'generated_at')
    readonly_fields = ('file_size_display', 'generated_at')
    extra = 0
    
    def file_size_display(self, obj):
        if obj.file_size:
            if obj.file_size < 1024:
                return f"{obj.file_size} B"
            elif obj.file_size < 1024 * 1024:
                return f"{obj.file_size / 1024:.1f} KB"
            else:
                return f"{obj.file_size / (1024 * 1024):.1f} MB"
        return "N/A"
    file_size_display.short_description = "File Size"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('ebook', 'generated_by')


@admin.register(EbookProject)
class EbookProjectAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'author_name', 'status', 'chapters_count', 
        'collaborators_count', 'cover_thumbnail', 'created_at', 'updated_at'
    ]
    list_filter = ['status', 'created_at', 'updated_at']
    search_fields = ['title', 'description', 'author__first_name', 'author__last_name', 'author__email']
    readonly_fields = ['id', 'created_at', 'updated_at', 'cover_thumbnail_large']
    filter_horizontal = ['collaborators']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'author', 'description', 'status')
        }),
        ('Cover Image', {
            'fields': ('cover_image', 'cover_thumbnail_large'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    inlines = [ChapterInline, EbookCollaboratorInline, EbookExportInline]
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('author').prefetch_related(
            'chapters', 'collaborators', 'exports'
        ).annotate(
            chapters_count=Count('chapters'),
            collaborators_count=Count('collaborators')
        )
    
    def author_name(self, obj):
        return obj.author.display_name if hasattr(obj.author, 'display_name') else str(obj.author)
    author_name.short_description = "Author"
    author_name.admin_order_field = 'author__first_name'
    
    def chapters_count(self, obj):
        return obj.chapters_count
    chapters_count.short_description = "Chapters"
    chapters_count.admin_order_field = 'chapters_count'
    
    def collaborators_count(self, obj):
        return obj.collaborators_count
    collaborators_count.short_description = "Collaborators"
    collaborators_count.admin_order_field = 'collaborators_count'
    
    def cover_thumbnail(self, obj):
        if obj.cover_image:
            return format_html(
                '<img src="{}" width="50" height="50" style="object-fit: cover;" />',
                obj.cover_image.url
            )
        return "No Cover"
    cover_thumbnail.short_description = "Cover"
    
    def cover_thumbnail_large(self, obj):
        if obj.cover_image:
            return format_html(
                '<img src="{}" width="200" height="200" style="object-fit: cover;" />',
                obj.cover_image.url
            )
        return "No Cover Image"
    cover_thumbnail_large.short_description = "Cover Preview"
    
    actions = ['make_published', 'make_draft', 'make_archived']
    
    def make_published(self, request, queryset):
        updated = queryset.update(status=EbookProject.Status.PUBLISHED)
        self.message_user(request, f"{updated} ebooks were marked as published.")
    make_published.short_description = "Mark selected ebooks as published"
    
    def make_draft(self, request, queryset):
        updated = queryset.update(status=EbookProject.Status.DRAFT)
        self.message_user(request, f"{updated} ebooks were marked as draft.")
    make_draft.short_description = "Mark selected ebooks as draft"
    
    def make_archived(self, request, queryset):
        updated = queryset.update(status=EbookProject.Status.ARCHIVED)
        self.message_user(request, f"{updated} ebooks were archived.")
    make_archived.short_description = "Archive selected ebooks"


@admin.register(EbookCollaborator)
class EbookCollaboratorAdmin(admin.ModelAdmin):
    list_display = ['ebook_title', 'user_name', 'role', 'permissions', 'joined_at']
    list_filter = ['role', 'can_edit', 'can_export', 'joined_at']
    search_fields = [
        'ebook__title', 'user__first_name', 'user__last_name', 
        'user__email', 'ebook__author__first_name', 'ebook__author__last_name'
    ]
    readonly_fields = ['joined_at']
    
    fieldsets = (
        ('Collaboration Details', {
            'fields': ('ebook', 'user', 'role')
        }),
        ('Permissions', {
            'fields': ('can_edit', 'can_export')
        }),
        ('Metadata', {
            'fields': ('joined_at',),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('ebook', 'user', 'ebook__author')
    
    def ebook_title(self, obj):
        return obj.ebook.title
    ebook_title.short_description = "Ebook"
    ebook_title.admin_order_field = 'ebook__title'
    
    def user_name(self, obj):
        return obj.user.display_name if hasattr(obj.user, 'display_name') else str(obj.user)
    user_name.short_description = "User"
    user_name.admin_order_field = 'user__first_name'
    
    def permissions(self, obj):
        perms = []
        if obj.can_edit:
            perms.append("Edit")
        if obj.can_export:
            perms.append("Export")
        return ", ".join(perms) if perms else "View Only"
    permissions.short_description = "Permissions"


@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ['title', 'ebook_title', 'order', 'is_draft', 'word_count', 'updated_at']
    list_filter = ['is_draft', 'ebook__status', 'updated_at', 'created_at']
    search_fields = ['title', 'ebook__title', 'ebook__author__first_name', 'ebook__author__last_name']
    readonly_fields = ['created_at', 'updated_at', 'word_count', 'content_preview']
    
    fieldsets = (
        ('Chapter Information', {
            'fields': ('ebook', 'title', 'order', 'is_draft')
        }),
        ('Content', {
            'fields': ('content', 'content_preview', 'word_count')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('ebook', 'ebook__author')
    
    def ebook_title(self, obj):
        return obj.ebook.title
    ebook_title.short_description = "Ebook"
    ebook_title.admin_order_field = 'ebook__title'
    
    def word_count(self, obj):
        if obj.content:
            # Simple word count estimation from JSON content
            # This is a basic implementation - you might want to improve it
            content_str = str(obj.content)
            words = len(content_str.split())
            return f"~{words} words"
        return "0 words"
    word_count.short_description = "Word Count"
    
    def content_preview(self, obj):
        if obj.content:
            content_str = str(obj.content)[:200]
            return format_html(
                '<div style="max-width: 400px; white-space: pre-wrap;">{}</div>',
                content_str + "..." if len(str(obj.content)) > 200 else content_str
            )
        return "No content"
    content_preview.short_description = "Content Preview"
    
    actions = ['make_draft', 'make_published']
    
    def make_draft(self, request, queryset):
        updated = queryset.update(is_draft=True)
        self.message_user(request, f"{updated} chapters were marked as draft.")
    make_draft.short_description = "Mark selected chapters as draft"
    
    def make_published(self, request, queryset):
        updated = queryset.update(is_draft=False)
        self.message_user(request, f"{updated} chapters were published.")
    make_published.short_description = "Publish selected chapters"


@admin.register(EbookExport)
class EbookExportAdmin(admin.ModelAdmin):
    list_display = [
        'ebook_title', 'format', 'version', 'file_size_display', 
        'download_count', 'generated_by_name', 'generated_at'
    ]
    list_filter = ['format', 'generated_at']
    search_fields = [
        'ebook__title', 'version', 'generated_by__first_name', 
        'generated_by__last_name', 'generated_by__email'
    ]
    readonly_fields = ['generated_at', 'file_size_display', 'download_link']
    
    fieldsets = (
        ('Export Information', {
            'fields': ('ebook', 'format', 'version', 'generated_by')
        }),
        ('File Details', {
            'fields': ('file', 'download_link', 'file_size_display', 'download_count')
        }),
        ('Metadata', {
            'fields': ('generated_at',),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('ebook', 'generated_by', 'ebook__author')
    
    def ebook_title(self, obj):
        return obj.ebook.title
    ebook_title.short_description = "Ebook"
    ebook_title.admin_order_field = 'ebook__title'
    
    def generated_by_name(self, obj):
        if obj.generated_by:
            return obj.generated_by.display_name if hasattr(obj.generated_by, 'display_name') else str(obj.generated_by)
        return "System"
    generated_by_name.short_description = "Generated By"
    generated_by_name.admin_order_field = 'generated_by__first_name'
    
    def file_size_display(self, obj):
        if obj.file_size:
            if obj.file_size < 1024:
                return f"{obj.file_size} B"
            elif obj.file_size < 1024 * 1024:
                return f"{obj.file_size / 1024:.1f} KB"
            else:
                return f"{obj.file_size / (1024 * 1024):.1f} MB"
        return "N/A"
    file_size_display.short_description = "File Size"
    
    def download_link(self, obj):
        if obj.file:
            return format_html(
                '<a href="{}" target="_blank">Download {}</a>',
                obj.file.url,
                obj.format
            )
        return "No file"
    download_link.short_description = "Download"


# Customize admin site headers
admin.site.site_header = "Ebook Management System"
admin.site.site_title = "Ebook Admin"
admin.site.index_title = "Welcome to Ebook Administration"


@admin.register(EbookTemplate)
class EbookTemplateAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'type', 'thumbnail_preview', 'is_default', 
        'is_premium', 'created_at', 'updated_at'
    ]
    list_filter = ['type', 'is_default', 'is_premium', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at', 'thumbnail_large', 'cover_preview']
    
    fieldsets = (
        ('Template Information', {
            'fields': ('name', 'description', 'type')
        }),
        ('Settings', {
            'fields': ('is_default', 'is_premium')
        }),
        ('Media', {
            'fields': ('thumbnail', 'thumbnail_large', 'cover_image', 'cover_preview'),
            'classes': ('collapse',)
        }),
        ('Template Data', {
            'fields': ('styles', 'structure'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def thumbnail_preview(self, obj):
        if obj.thumbnail:
            return format_html(
                '<img src="{}" width="50" height="50" style="object-fit: cover; border-radius: 4px;" />',
                obj.thumbnail.url
            )
        return "No Thumbnail"
    thumbnail_preview.short_description = "Preview"
    
    def thumbnail_large(self, obj):
        if obj.thumbnail:
            return format_html(
                '<img src="{}" width="200" height="200" style="object-fit: cover; border-radius: 8px;" />',
                obj.thumbnail.url
            )
        return "No Thumbnail"
    thumbnail_large.short_description = "Thumbnail Preview"
    
    def cover_preview(self, obj):
        if obj.cover_image:
            return format_html(
                '<img src="{}" width="150" height="200" style="object-fit: cover; border-radius: 8px;" />',
                obj.cover_image.url
            )
        return "No Cover Image"
    cover_preview.short_description = "Cover Preview"
    
    actions = ['make_default', 'remove_default', 'make_premium', 'make_free']
    
    def make_default(self, request, queryset):
        for template in queryset:
            # This will automatically handle the uniqueness constraint
            template.is_default = True
            template.save()
        self.message_user(request, f"Selected templates were set as default for their types.")
    make_default.short_description = "Set as default templates"
    
    def remove_default(self, request, queryset):
        updated = queryset.update(is_default=False)
        self.message_user(request, f"{updated} templates were removed from default status.")
    remove_default.short_description = "Remove default status"
    
    def make_premium(self, request, queryset):
        updated = queryset.update(is_premium=True)
        self.message_user(request, f"{updated} templates were marked as premium.")
    make_premium.short_description = "Mark as premium"
    
    def make_free(self, request, queryset):
        updated = queryset.update(is_premium=False)
        self.message_user(request, f"{updated} templates were marked as free.")
    make_free.short_description = "Mark as free"


@admin.register(UserTemplate)
class UserTemplateAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'user_name', 'base_template_name', 'base_template_type',
        'created_at', 'updated_at'
    ]
    list_filter = ['base_template__type', 'created_at', 'updated_at']
    search_fields = [
        'name', 'user__first_name', 'user__last_name', 
        'user__email', 'base_template__name'
    ]
    readonly_fields = ['created_at', 'updated_at', 'styles_preview', 'structure_preview']
    
    fieldsets = (
        ('Template Information', {
            'fields': ('user', 'base_template', 'name')
        }),
        ('Customizations', {
            'fields': ('styles', 'styles_preview', 'structure', 'structure_preview'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'base_template')
    
    def user_name(self, obj):
        return obj.user.display_name if hasattr(obj.user, 'display_name') else str(obj.user)
    user_name.short_description = "User"
    user_name.admin_order_field = 'user__first_name'
    
    def base_template_name(self, obj):
        return obj.base_template.name if obj.base_template else "Custom"
    base_template_name.short_description = "Base Template"
    base_template_name.admin_order_field = 'base_template__name'
    
    def base_template_type(self, obj):
        return obj.base_template.get_type_display() if obj.base_template else "N/A"
    base_template_type.short_description = "Type"
    
    def styles_preview(self, obj):
        if obj.styles:
            styles_str = str(obj.styles)[:300]
            return format_html(
                '<pre style="max-width: 500px; white-space: pre-wrap; font-size: 11px;">{}</pre>',
                styles_str + "..." if len(str(obj.styles)) > 300 else styles_str
            )
        return "No custom styles"
    styles_preview.short_description = "Styles Preview"
    
    def structure_preview(self, obj):
        if obj.structure:
            structure_str = str(obj.structure)[:300]
            return format_html(
                '<pre style="max-width: 500px; white-space: pre-wrap; font-size: 11px;">{}</pre>',
                structure_str + "..." if len(str(obj.structure)) > 300 else structure_str
            )
        return "No custom structure"
    structure_preview.short_description = "Structure Preview"