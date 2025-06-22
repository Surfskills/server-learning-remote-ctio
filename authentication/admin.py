from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import User, Profile


class ProfileInline(admin.StackedInline):
    model = Profile
    fields = (
        ('bio', 'location'),
        ('website', 'company', 'timezone'),
        ('linkedin_url', 'github_url', 'twitter_url'),
        ('email_notifications', 'sms_notifications')
    )
    extra = 0


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    # Inherit from BaseUserAdmin but customize for email-based authentication
    inlines = [ProfileInline]
    
    list_display = [
        'email', 'full_name_display', 'user_type', 'profile_completion_display',
        'is_active', 'is_staff', 'profile_picture_display', 'created_at'
    ]
    
    list_filter = [
        'user_type', 'is_active', 'is_staff', 'is_superuser',
        'is_profile_complete', 'created_at'
    ]
    
    search_fields = ['email', 'first_name', 'last_name', 'phone_number']
    
    ordering = ['-created_at']
    
    readonly_fields = [
        'created_at', 'updated_at', 'last_login', 
        'profile_completion_percentage', 'is_profile_complete'
    ]
    
    # Custom fieldsets for better organization
    fieldsets = (
        ('Authentication', {
            'fields': ('email', 'password')
        }),
        ('Personal Information', {
            'fields': (
                ('first_name', 'last_name'),
                'phone_number',
                'profile_picture'
            )
        }),
        ('Account Type & Status', {
            'fields': (
                'user_type',
                ('is_active', 'is_staff', 'is_superuser')
            )
        }),
        ('Profile Completion', {
            'fields': (
                'profile_completion_percentage',
                'is_profile_complete'
            ),
            'classes': ('collapse',)
        }),
        ('Permissions', {
            'fields': ('groups', 'user_permissions'),
            'classes': ('collapse',)
        }),
        ('Important Dates', {
            'fields': ('last_login', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    # FIXED: Fieldsets for adding new users - removed username field
    add_fieldsets = (
        ('Required Information', {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'user_type'),
        }),
        ('Optional Information', {
            'classes': ('wide', 'collapse'),
            'fields': (
                ('first_name', 'last_name'),
                'phone_number',
                'profile_picture'
            ),
        }),
        ('Permissions', {
            'classes': ('wide', 'collapse'),
            'fields': ('is_active', 'is_staff', 'is_superuser'),
        }),
    )
    
    # Override the add_form_template if needed
    add_form_template = None
    
    # Custom display methods
    def full_name_display(self, obj):
        if obj.full_name:
            return obj.full_name
        return format_html('<em>No name set</em>')
    full_name_display.short_description = 'Full Name'
    full_name_display.admin_order_field = 'first_name'
    
    def profile_completion_display(self, obj):
        percentage = obj.profile_completion_percentage
        if percentage >= 80:
            color = '#28a745'  # Green
            icon = '✓'
        elif percentage >= 50:
            color = '#ffc107'  # Yellow
            icon = '○'
        else:
            color = '#dc3545'  # Red
            icon = '●'
        
        return format_html(
            '<span style="color: {};">{} {}%</span>',
            color, icon, percentage
        )
    profile_completion_display.short_description = 'Profile Complete'
    profile_completion_display.admin_order_field = 'profile_completion_percentage'
    
    def profile_picture_display(self, obj):
        if obj.profile_picture:
            return format_html(
                '<img src="{}" width="30" height="30" style="border-radius: 50%;" />',
                obj.profile_picture.url
            )
        return format_html('<span style="color: #6c757d;">No image</span>')
    profile_picture_display.short_description = 'Avatar'
    
    # Custom actions
    actions = ['make_active', 'make_inactive', 'promote_to_instructor', 'demote_to_student']
    
    def make_active(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(
            request,
            f'{updated} user(s) were successfully marked as active.'
        )
    make_active.short_description = 'Mark selected users as active'
    
    def make_inactive(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(
            request,
            f'{updated} user(s) were successfully marked as inactive.'
        )
    make_inactive.short_description = 'Mark selected users as inactive'
    
    def promote_to_instructor(self, request, queryset):
        updated = queryset.filter(user_type=User.Types.STUDENT).update(
            user_type=User.Types.INSTRUCTOR
        )
        self.message_user(
            request,
            f'{updated} student(s) were successfully promoted to instructor.'
        )
    promote_to_instructor.short_description = 'Promote students to instructors'
    
    def demote_to_student(self, request, queryset):
        updated = queryset.filter(user_type=User.Types.INSTRUCTOR).update(
            user_type=User.Types.STUDENT
        )
        self.message_user(
            request,
            f'{updated} instructor(s) were successfully demoted to student.'
        )
    demote_to_student.short_description = 'Demote instructors to students'
    
    # Override get_queryset to add annotations for better performance
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        # Add any annotations here if needed for performance
        return queryset
    
    # Handle password field display
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj:
            # For existing users, make password field readonly in a user-friendly way
            if 'password' in form.base_fields:
                form.base_fields['password'].help_text = (
                    'Raw passwords are not stored, so there is no way to see this user\'s password, '
                    'but you can change the password using <a href="../password/">this form</a>.'
                )
        return form


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = [
        'user_email', 'user_full_name', 'user_type', 'location', 
        'company', 'has_social_links', 'notification_preferences', 'updated_at'
    ]
    
    list_filter = [
        'user__user_type', 'email_notifications', 'sms_notifications',
        'location', 'company', 'updated_at'
    ]
    
    search_fields = [
        'user__email', 'user__first_name', 'user__last_name',
        'bio', 'location', 'company', 'website'
    ]
    
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Profile Details', {
            'fields': (
                'bio',
                ('location', 'company'),
                ('website', 'timezone')
            )
        }),
        ('Social Links', {
            'fields': ('linkedin_url', 'github_url', 'twitter_url'),
            'classes': ('collapse',)
        }),
        ('Notification Preferences', {
            'fields': ('email_notifications', 'sms_notifications')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    # Custom display methods
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Email'
    user_email.admin_order_field = 'user__email'
    
    def user_full_name(self, obj):
        if obj.user.full_name:
            return obj.user.full_name
        return format_html('<em>No name set</em>')
    user_full_name.short_description = 'Full Name'
    user_full_name.admin_order_field = 'user__first_name'
    
    def user_type(self, obj):
        return obj.user.get_user_type_display()
    user_type.short_description = 'User Type'
    user_type.admin_order_field = 'user__user_type'
    
    def has_social_links(self, obj):
        links = [obj.linkedin_url, obj.github_url, obj.twitter_url]
        active_links = sum(1 for link in links if link)
        
        if active_links == 0:
            return format_html('<span style="color: #6c757d;">None</span>')
        elif active_links == len(links):
            return format_html('<span style="color: #28a745;">All ({})</span>', active_links)
        else:
            return format_html('<span style="color: #ffc107;">{} of {}</span>', active_links, len(links))
    has_social_links.short_description = 'Social Links'
    
    def notification_preferences(self, obj):
        email_icon = '📧' if obj.email_notifications else '📧̶'
        sms_icon = '📱' if obj.sms_notifications else '📱̶'
        return format_html('{} {}', email_icon, sms_icon)
    notification_preferences.short_description = 'Notifications'
    
    # Custom actions
    actions = ['enable_all_notifications', 'disable_all_notifications', 'enable_email_only']
    
    def enable_all_notifications(self, request, queryset):
        updated = queryset.update(email_notifications=True, sms_notifications=True)
        self.message_user(
            request,
            f'{updated} profile(s) were updated to enable all notifications.'
        )
    enable_all_notifications.short_description = 'Enable all notifications'
    
    def disable_all_notifications(self, request, queryset):
        updated = queryset.update(email_notifications=False, sms_notifications=False)
        self.message_user(
            request,
            f'{updated} profile(s) were updated to disable all notifications.'
        )
    disable_all_notifications.short_description = 'Disable all notifications'
    
    def enable_email_only(self, request, queryset):
        updated = queryset.update(email_notifications=True, sms_notifications=False)
        self.message_user(
            request,
            f'{updated} profile(s) were updated to enable email notifications only.'
        )
    enable_email_only.short_description = 'Enable email notifications only'


# Custom admin site configuration
admin.site.site_header = 'Learning Management System'
admin.site.site_title = 'LMS Admin'
admin.site.index_title = 'Welcome to LMS Administration'