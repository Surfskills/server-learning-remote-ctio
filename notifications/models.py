# notifications/models.py
from django.db import models
from core.models import BaseModel
from authentication.models import User
from courses.models import Course

class Notification(BaseModel):
    NOTIFICATION_TYPES = [
        ('system', 'System'),
        ('course', 'Course'),
        ('enrollment', 'Enrollment'),
        ('announcement', 'Announcement'),
        ('deadline', 'Deadline'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    related_course = models.ForeignKey(
        Course, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    action_url = models.URLField(max_length=500, blank=True, null=True)
    scheduled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['scheduled_at']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.title}"

class NotificationPreference(BaseModel):
    # Fixed: Remove primary_key=True since BaseModel already provides primary key
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='notification_preferences'
    )
    email_enabled = models.BooleanField(default=True)
    push_enabled = models.BooleanField(default=True)
    in_app_enabled = models.BooleanField(default=True)
    digest_frequency = models.CharField(
        max_length=10,
        choices=[
            ('immediate', 'Immediate'),
            ('daily', 'Daily'),
            ('weekly', 'Weekly')
        ],
        default='immediate'
    )
    course_updates = models.BooleanField(default=True)
    deadline_reminders = models.BooleanField(default=True)
    new_content = models.BooleanField(default=True)
    announcement_notifications = models.BooleanField(default=True)

    def __str__(self):
        return f"Preferences for {self.user.email}"

