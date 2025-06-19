from django.db import models
from django.contrib.auth import get_user_model
from core.models import BaseModel

User = get_user_model()

class UserProfile(BaseModel):
    """
    Extended user profile model that builds upon the basic Profile in authentication app
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='extended_profile')
    headline = models.CharField(max_length=255, blank=True)
    bio = models.TextField(blank=True)
    skills = models.JSONField(default=list, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
    education = models.JSONField(default=list, blank=True)
    experience = models.JSONField(default=list, blank=True)
    social_links = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"Extended Profile for {self.user.email}"

class UserActivity(BaseModel):
    """
    Tracks user activities across the platform
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activities')
    activity_type = models.CharField(max_length=100)
    details = models.JSONField(default=dict)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "User Activities"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - {self.activity_type}"

class UserPreference(BaseModel):
    """
    Stores user preferences and settings
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='preferences')
    notification_settings = models.JSONField(default=dict)
    privacy_settings = models.JSONField(default=dict)
    ui_settings = models.JSONField(default=dict)
    content_preferences = models.JSONField(default=dict)

    def __str__(self):
        return f"Preferences for {self.user.email}"

class UserRole(BaseModel):
    """
    Defines additional roles and permissions beyond the basic user types
    """
    ROLE_CHOICES = [
        ('CONTENT_CREATOR', 'Content Creator'),
        ('MODERATOR', 'Moderator'),
        ('REVIEWER', 'Reviewer'),
        ('SUPPORT', 'Support'),
        ('ANALYST', 'Analyst'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='roles')
    role = models.CharField(max_length=50, choices=ROLE_CHOICES)
    permissions = models.JSONField(default=list)
    is_active = models.BooleanField(default=True)
    granted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='granted_roles')

    class Meta:
        unique_together = ('user', 'role')

    def __str__(self):
        return f"{self.user.email} - {self.role}"

class UserDevice(BaseModel):
    """
    Tracks user devices for authentication and notifications
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='devices')
    device_id = models.CharField(max_length=255)
    device_name = models.CharField(max_length=255, blank=True)
    device_type = models.CharField(max_length=50)
    os_version = models.CharField(max_length=50, blank=True)
    app_version = models.CharField(max_length=50, blank=True)
    fcm_token = models.CharField(max_length=255, blank=True)
    last_active = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('user', 'device_id')

    def __str__(self):
        return f"{self.user.email} - {self.device_name or self.device_id}"