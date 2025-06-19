from django.db import models

from core.models import BaseModel
from authentication.models import User
from courses.models import Course, Lecture

class DiscussionThread(BaseModel):
    THREAD_TYPES = [
        ('qna', 'Q&A'),
        ('discussion', 'Discussion'),
        ('announcement', 'Announcement'),
    ]
    
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='threads')
    lecture = models.ForeignKey(
        Lecture, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='threads'
    )
    started_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='started_threads')
    title = models.CharField(max_length=200)
    content = models.TextField()
    thread_type = models.CharField(max_length=20, choices=THREAD_TYPES)
    is_pinned = models.BooleanField(default=False)
    is_closed = models.BooleanField(default=False)
    view_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-is_pinned', '-created_at']
        indexes = [
            models.Index(fields=['course', 'lecture']),
            models.Index(fields=['started_by', 'created_at']),
        ]

    def __str__(self):
        return f"{self.title} ({self.get_thread_type_display()})"

class ThreadReply(BaseModel):
    thread = models.ForeignKey(DiscussionThread, on_delete=models.CASCADE, related_name='replies')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='thread_replies')
    content = models.TextField()
    is_answer = models.BooleanField(default=False)
    upvotes = models.PositiveIntegerField(default=0)
    parent_reply = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='child_replies'
    )

    class Meta:
        ordering = ['created_at']
        verbose_name_plural = "Thread replies"

    def __str__(self):
        return f"Reply by {self.author.email} on {self.thread.title}"

class Upvote(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='upvotes_given')
    reply = models.ForeignKey(ThreadReply, on_delete=models.CASCADE, related_name='upvote_instances')

    class Meta:
        unique_together = ['user', 'reply']

    def __str__(self):
        return f"Upvote by {self.user.email}"

class UserEngagement(BaseModel):
    ENGAGEMENT_TYPES = [
        ('view', 'View'),
        ('reply', 'Reply'),
        ('upvote', 'Upvote'),
        ('share', 'Share'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='engagements')
    thread = models.ForeignKey(
        DiscussionThread, 
        on_delete=models.CASCADE, 
        null=True,
        blank=True,
        related_name='engagements'
    )
    reply = models.ForeignKey(
        ThreadReply,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='engagements'
    )
    engagement_type = models.CharField(max_length=10, choices=ENGAGEMENT_TYPES)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'engagement_type']),
        ]

    def __str__(self):
        return f"{self.get_engagement_type_display()} by {self.user.email}"