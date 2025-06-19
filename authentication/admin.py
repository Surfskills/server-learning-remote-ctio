from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import User, Profile


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Profile'
    fields = (
        'bio', 'location', 'website', 'company', 'timezone',
        'linkedin_url', 'github_url', 'twitter_url',
        'email_notifications', 'sms_notifications'
    )


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)
    
    list_display = (
        'email', 'full_name', 'user_type', 'profile_completion_display',
        'is_active', 'is_staff', 'created_at'
    )
    list_filter = (
        'user_type', 'is_active', 'is_staff', 'is_superuser', 
        'is_profile_complete', 'created_at'
    )
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('-created_at',)
    
    fieldsets = (
        (None, {
            'fields': ('email', 'password')
        }),
        ('Personal Info', {
            'fields': (
                'first_name', 'last_name', 'phone_number', 
                'profile_picture', 'user_type'
            )
        }),
        ('Profile Completion', {
            'fields': ('profile_completion_percentage', 'is_profile_complete'),
            'classes': ('collapse',)
        }),
        ('Permissions', {
            'fields': (
                'is_active', 'is_staff', 'is_superuser',
                'groups', 'user_permissions'
            ),
            'classes': ('collapse',)
        }),
        ('Important dates', {
            'fields': ('last_login', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email', 'password1', 'password2', 'user_type',
                'first_name', 'last_name'
            ),
        }),
    )
    
    readonly_fields = (
        'created_at', 'updated_at', 'last_login', 
        'profile_completion_percentage', 'is_profile_complete'
    )
    
    def profile_completion_display(self, obj):
        """Display profile completion as a progress bar"""
        percentage = obj.profile_completion_percentage
        color = 'green' if percentage >= 80 else 'orange' if percentage >= 50 else 'red'
        
        return format_html(
            '<div style="width: 100px; background-color: #f0f0f0; border-radius: 3px;">'
            '<div style="width: {}%; background-color: {}; height: 20px; border-radius: 3px; text-align: center; color: white; font-size: 12px; line-height: 20px;">'
            '{}%'
            '</div></div>',
            percentage, color, percentage
        )
    profile_completion_display.short_description = 'Profile Completion'
    
    def full_name(self, obj):
        return obj.full_name or '-'
    full_name.short_description = 'Full Name'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('profile')
    
    actions = ['calculate_profile_completion', 'activate_users', 'deactivate_users']
    
    def calculate_profile_completion(self, request, queryset):
        """Admin action to recalculate profile completion for selected users"""
        count = 0
        for user in queryset:
            user.calculate_profile_completion()
            count += 1
        
        self.message_user(
            request,
            f'Profile completion recalculated for {count} users.'
        )
    calculate_profile_completion.short_description = "Recalculate profile completion"
    
    def activate_users(self, request, queryset):
        """Admin action to activate selected users"""
        count = queryset.update(is_active=True)
        self.message_user(
            request,
            f'{count} users have been activated.'
        )
    activate_users.short_description = "Activate selected users"
    
    def deactivate_users(self, request, queryset):
        """Admin action to deactivate selected users"""
        count = queryset.update(is_active=False)
        self.message_user(
            request,
            f'{count} users have been deactivated.'
        )
    deactivate_users.short_description = "Deactivate selected users"


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'user_email', 'location', 'company', 
        'email_notifications', 'sms_notifications', 'updated_at'
    )
    list_filter = (
        'email_notifications', 'sms_notifications', 
        'location', 'company', 'created_at'
    )
    search_fields = (
        'user__email', 'user__first_name', 'user__last_name',
        'bio', 'location', 'company'
    )
    ordering = ('-updated_at',)
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'bio', 'location', 'company', 'timezone')
        }),
        ('Links', {
            'fields': ('website', 'linkedin_url', 'github_url', 'twitter_url'),
            'classes': ('collapse',)
        }),
        ('Notifications', {
            'fields': ('email_notifications', 'sms_notifications')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User Email'
    user_email.admin_order_field = 'user__email'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


# Admin site customization
admin.site.site_header = "User Management Admin"
admin.site.site_title = "User Management"
admin.site.index_title = "Welcome to User Management Administration"