from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.db.models import Count, Q
from django.urls import reverse
from django.utils import timezone
from .models import EbookProject, EbookCollaborator, Chapter, EbookExport


class EbookCollaboratorInline(admin.TabularInline):
    model = EbookCollaborator
    extra = 0
    fields = ['user', 'role', 'can_edit', 'can_export', 'joined_at']
    readonly_fields = ['joined_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


class ChapterInline(admin.TabularInline):
    model = Chapter
    extra = 0
    fields = ['order', 'title', 'is_draft', 'created_at']
    readonly_fields = ['created_at']
    ordering = ['order']


class EbookExportInline(admin.TabularInline):
    model = EbookExport
    extra = 0
    fields = ['format', 'file', 'generated_by', 'generated_at', 'file_size', 'download_count']
    readonly_fields = ['generated_at', 'file_size', 'download_count']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('generated_by')


@admin.register(EbookProject)
class EbookProjectAdmin(admin.ModelAdmin):
    list_display = [
        'title', 
        'author', 
        'status', 
        'cover_preview',
        'chapter_count',
        'collaborator_count',
        'export_count',
        'created_at',
        'updated_at'
    ]
    list_filter = [
        'status', 
        'created_at', 
        'updated_at',
        ('deleted_at', admin.EmptyFieldListFilter)
    ]
    search_fields = ['title', 'description', 'author__email', 'author__display_name']
    readonly_fields = [
        'id', 
        'created_at', 
        'updated_at', 
        'cover_preview',
        'chapter_count',
        'collaborator_count',
        'export_count'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'title', 'author', 'description', 'status')
        }),
        ('Media', {
            'fields': ('cover_image', 'cover_preview')
        }),
        ('Template Configuration', {
            'fields': ('template_styles', 'template_structure'),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': ('chapter_count', 'collaborator_count', 'export_count'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'deleted_at'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [EbookCollaboratorInline, ChapterInline, EbookExportInline]
    
    def cover_preview(self, obj):
        if obj.cover_image:
            return format_html(
                '<img src="{}" style="max-height: 100px; max-width: 150px;" />',
                obj.cover_image.url
            )
        return "No cover"
    cover_preview.short_description = "Cover Preview"
    
    def chapter_count(self, obj):
        return obj.chapters.count()
    chapter_count.short_description = "Chapters"
    
    def collaborator_count(self, obj):
        return obj.collaborators.count()
    collaborator_count.short_description = "Collaborators"
    
    def export_count(self, obj):
        return obj.exports.count()
    export_count.short_description = "Exports"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('author').prefetch_related(
            'chapters', 'collaborators', 'exports'
        ).annotate(
            chapter_count=Count('chapters', distinct=True),
            collaborator_count=Count('collaborators', distinct=True),
            export_count=Count('exports', distinct=True)
        )
    
    actions = ['mark_as_published', 'mark_as_draft', 'mark_as_archived', 'soft_delete']
    
    def mark_as_published(self, request, queryset):
        updated = queryset.update(status=EbookProject.Status.PUBLISHED)
        self.message_user(request, f"{updated} ebooks marked as published.")
    mark_as_published.short_description = "Mark as published"
    
    def mark_as_draft(self, request, queryset):
        updated = queryset.update(status=EbookProject.Status.DRAFT)
        self.message_user(request, f"{updated} ebooks marked as draft.")
    mark_as_draft.short_description = "Mark as draft"
    
    def mark_as_archived(self, request, queryset):
        updated = queryset.update(status=EbookProject.Status.ARCHIVED)
        self.message_user(request, f"{updated} ebooks archived.")
    mark_as_archived.short_description = "Archive ebooks"
    
    def soft_delete(self, request, queryset):
        updated = queryset.update(deleted_at=timezone.now())
        self.message_user(request, f"{updated} ebooks soft deleted.")
    soft_delete.short_description = "Soft delete ebooks"


@admin.register(EbookCollaborator)
class EbookCollaboratorAdmin(admin.ModelAdmin):
    list_display = [
        'user', 
        'ebook', 
        'role', 
        'can_edit', 
        'can_export', 
        'joined_at'
    ]
    list_filter = [
        'role', 
        'can_edit', 
        'can_export', 
        'joined_at'
    ]
    search_fields = [
        'user__email', 
        'user__display_name', 
        'ebook__title'
    ]
    readonly_fields = ['joined_at']
    
    fieldsets = (
        ('Collaboration Details', {
            'fields': ('ebook', 'user', 'role')
        }),
        ('Permissions', {
            'fields': ('can_edit', 'can_export')
        }),
        ('Timestamps', {
            'fields': ('joined_at',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'ebook')


@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = [
        'title', 
        'ebook', 
        'order', 
        'is_draft', 
        'word_count',
        'created_at', 
        'updated_at'
    ]
    list_filter = [
        'is_draft', 
        'created_at', 
        'updated_at',
        'ebook__status'
    ]
    search_fields = [
        'title', 
        'ebook__title', 
        'ebook__author__display_name'
    ]
    readonly_fields = ['created_at', 'updated_at', 'word_count']
    
    fieldsets = (
        ('Chapter Information', {
            'fields': ('ebook', 'title', 'order', 'is_draft')
        }),
        ('Content', {
            'fields': ('content', 'word_count')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def word_count(self, obj):
        # Simple word count estimation from JSON content
        if obj.content and isinstance(obj.content, dict):
            text_content = self._extract_text_from_json(obj.content)
            return len(text_content.split()) if text_content else 0
        return 0
    word_count.short_description = "Word Count"
    
    def _extract_text_from_json(self, content):
        """Extract text content from TipTap/ProseMirror JSON structure"""
        text = ""
        if isinstance(content, dict):
            if content.get('type') == 'text':
                text += content.get('text', '')
            elif 'content' in content:
                for item in content['content']:
                    text += self._extract_text_from_json(item)
        elif isinstance(content, list):
            for item in content:
                text += self._extract_text_from_json(item)
        return text
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('ebook', 'ebook__author')
    
    actions = ['mark_as_draft', 'mark_as_final']
    
    def mark_as_draft(self, request, queryset):
        updated = queryset.update(is_draft=True)
        self.message_user(request, f"{updated} chapters marked as draft.")
    mark_as_draft.short_description = "Mark as draft"
    
    def mark_as_final(self, request, queryset):
        updated = queryset.update(is_draft=False)
        self.message_user(request, f"{updated} chapters marked as final.")
    mark_as_final.short_description = "Mark as final"


@admin.register(EbookExport)
class EbookExportAdmin(admin.ModelAdmin):
    list_display = [
        'ebook', 
        'format', 
        'generated_by', 
        'file_size_display',
        'download_count', 
        'generated_at'
    ]
    list_filter = [
        'format', 
        'generated_at',
        'ebook__status'
    ]
    search_fields = [
        'ebook__title', 
        'ebook__author__display_name',
        'generated_by__display_name'
    ]
    readonly_fields = [
        'generated_at', 
        'file_size', 
        'file_size_display',
        'download_count'
    ]
    
    fieldsets = (
        ('Export Information', {
            'fields': ('ebook', 'format', 'version', 'generated_by')
        }),
        ('File Details', {
            'fields': ('file', 'file_size_display', 'download_count')
        }),
        ('Timestamps', {
            'fields': ('generated_at',)
        }),
    )
    
    def file_size_display(self, obj):
        """Display file size in human readable format"""
        if obj.file_size:
            if obj.file_size < 1024:
                return f"{obj.file_size} B"
            elif obj.file_size < 1024 * 1024:
                return f"{obj.file_size / 1024:.1f} KB"
            else:
                return f"{obj.file_size / (1024 * 1024):.1f} MB"
        return "Unknown"
    file_size_display.short_description = "File Size"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'ebook', 'ebook__author', 'generated_by'
        )
    
    actions = ['reset_download_count']
    
    def reset_download_count(self, request, queryset):
        updated = queryset.update(download_count=0)
        self.message_user(request, f"Reset download count for {updated} exports.")
    reset_download_count.short_description = "Reset download count"


# Optional: Custom admin site configuration
admin.site.site_header = "Ebook Manager Admin"
admin.site.site_title = "Ebook Admin"
admin.site.index_title = "Welcome to Ebook Management"