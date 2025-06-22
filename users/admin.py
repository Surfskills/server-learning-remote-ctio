from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django import forms
from .models import UserProfile, UserActivity, UserPreference, UserRole, UserDevice

User = get_user_model()

class CustomUserCreationForm(UserCreationForm):
    """Custom form for creating users with email instead of username"""
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('email', 'user_type', 'first_name', 'last_name')

class CustomUserChangeForm(UserChangeForm):
    """Custom form for changing users with email instead of username"""
    class Meta(UserChangeForm.Meta):
        model = User
        fields = '__all__'

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Extended Profile'
    fk_name = 'user'

class UserPreferenceInline(admin.StackedInline):
    model = UserPreference
    can_delete = False
    verbose_name_plural = 'Preferences'

class UserRoleInline(admin.TabularInline):
    model = UserRole
    extra = 1
    fk_name = 'user'
    verbose_name_plural = 'Additional Roles'

class UserDeviceInline(admin.TabularInline):
    model = UserDevice
    extra = 1
    verbose_name_plural = 'Devices'

class CustomUserAdmin(BaseUserAdmin):
    # Use custom forms
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm
    
    # Define fieldsets for existing users (without username)
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'phone_number', 'profile_picture')}),
        ('User Type', {'fields': ('user_type',)}),
        ('Profile Status', {'fields': ('is_profile_complete', 'profile_completion_percentage')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'created_at', 'updated_at')}),
    )
    
    # Define fieldsets for adding new users
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'user_type', 'password1', 'password2'),
        }),
        ('Personal info', {
            'classes': ('wide',),
            'fields': ('first_name', 'last_name', 'phone_number'),
        }),
        ('Permissions', {
            'classes': ('wide',),
            'fields': ('is_active', 'is_staff', 'is_superuser'),
        }),
    )
    
    # Configure list display and other options
    list_display = ('email', 'first_name', 'last_name', 'user_type', 'is_staff', 'is_active', 'created_at')
    list_filter = ('user_type', 'is_staff', 'is_active', 'is_superuser', 'created_at')
    search_fields = ('email', 'first_name', 'last_name', 'phone_number')
    ordering = ('-created_at',)
    filter_horizontal = ('groups', 'user_permissions')
    readonly_fields = ('created_at', 'updated_at', 'last_login', 'profile_completion_percentage', 'is_profile_complete')
    
    # Include inlines
    inlines = (UserProfileInline, UserPreferenceInline, UserRoleInline, UserDeviceInline)

    def get_inline_instances(self, request, obj=None):
        """Only show inlines for existing users, not when adding new users"""
        if not obj:
            return []
        return super().get_inline_instances(request, obj)

# Unregister the default User admin and register our custom one
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass  # User wasn't registered yet
admin.site.register(User, CustomUserAdmin)

@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    list_display = ('user', 'activity_type', 'created_at')
    list_filter = ('activity_type', 'created_at')
    search_fields = ('user__email', 'activity_type')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'headline', 'created_at')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'headline')
    list_filter = ('created_at',)
    readonly_fields = ('created_at', 'updated_at')

@admin.register(UserPreference)
class UserPreferenceAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at')
    search_fields = ('user__email',)
    readonly_fields = ('created_at', 'updated_at')

@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'is_active', 'granted_by', 'created_at')
    list_filter = ('role', 'is_active', 'created_at')
    search_fields = ('user__email', 'role')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(UserDevice)
class UserDeviceAdmin(admin.ModelAdmin):
    list_display = ('user', 'device_name', 'device_type', 'is_active', 'last_active')
    list_filter = ('device_type', 'is_active', 'last_active')
    search_fields = ('user__email', 'device_name', 'device_id')
    readonly_fields = ('created_at', 'updated_at', 'last_active')