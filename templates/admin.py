from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from .models import EbookTemplate, UserTemplate


@admin.register(EbookTemplate)
class EbookTemplateAdmin(admin.ModelAdmin):
    list_display = [
        'name', 
        'type', 
        'is_default', 
        'is_premium', 
        'thumbnail_preview',
        'created_at'
    ]
    list_filter = [
        'type', 
        'is_default', 
        'is_premium', 
        'created_at'
    ]
    search_fields = ['name', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at', 'thumbnail_preview']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'name', 'description', 'type')
        }),
        ('Settings', {
            'fields': ('is_default', 'is_premium')
        }),
        ('Media', {
            'fields': ('thumbnail', 'thumbnail_preview', 'cover_image')
        }),
        ('Template Configuration', {
            'fields': ('styles', 'structure'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def thumbnail_preview(self, obj):
        if obj.thumbnail:
            return format_html(
                '<img src="{}" style="max-height: 50px; max-width: 100px;" />',
                obj.thumbnail.url
            )
        return "No thumbnail"
    thumbnail_preview.short_description = "Preview"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related()
    
    actions = ['make_default', 'make_premium', 'make_free']
    
    def make_default(self, request, queryset):
        # Group by type to ensure we only set one default per type
        for template_type in EbookTemplate.TemplateType.values:
            type_templates = queryset.filter(type=template_type)
            if type_templates.exists():
                # Reset all defaults for this type
                EbookTemplate.objects.filter(type=template_type).update(is_default=False)
                # Set the first selected one as default
                type_templates.first().is_default = True
                type_templates.first().save()
        
        self.message_user(request, "Selected templates have been set as default for their types.")
    make_default.short_description = "Set as default template"
    
    def make_premium(self, request, queryset):
        updated = queryset.update(is_premium=True)
        self.message_user(request, f"{updated} templates marked as premium.")
    make_premium.short_description = "Mark as premium"
    
    def make_free(self, request, queryset):
        updated = queryset.update(is_premium=False)
        self.message_user(request, f"{updated} templates marked as free.")
    make_free.short_description = "Mark as free"


@admin.register(UserTemplate)
class UserTemplateAdmin(admin.ModelAdmin):
    list_display = [
        'name', 
        'user', 
        'base_template', 
        'created_at', 
        'updated_at'
    ]
    list_filter = [
        'created_at', 
        'updated_at',
        'base_template__type'
    ]
    search_fields = [
        'name', 
        'user__email', 
        'user__display_name',
        'base_template__name'
    ]
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'user', 'base_template')
        }),
        ('Template Configuration', {
            'fields': ('styles', 'structure'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'base_template')
    
    # Filter base_template choices based on available templates
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "base_template":
            kwargs["queryset"] = EbookTemplate.objects.all().order_by('type', 'name')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


# Optional: Inline admin for UserTemplate within User admin
class UserTemplateInline(admin.TabularInline):
    model = UserTemplate
    extra = 0
    readonly_fields = ['created_at', 'updated_at']
    fields = ['name', 'base_template', 'created_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('base_template')