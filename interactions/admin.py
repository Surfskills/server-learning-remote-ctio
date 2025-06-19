from django.contrib import admin
from .models import DiscussionThread, ThreadReply, Upvote, UserEngagement

@admin.register(DiscussionThread)
class DiscussionThreadAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'started_by', 'thread_type', 'is_pinned', 'is_closed', 'created_at')
    list_filter = ('thread_type', 'is_pinned', 'is_closed', 'course')
    search_fields = ('title', 'content', 'started_by__email')
    raw_id_fields = ('course', 'lecture', 'started_by')
    readonly_fields = ('view_count',)

@admin.register(ThreadReply)
class ThreadReplyAdmin(admin.ModelAdmin):
    list_display = ('thread', 'author', 'is_answer', 'upvotes', 'created_at')
    list_filter = ('is_answer', 'thread__course')
    search_fields = ('content', 'author__email', 'thread__title')
    raw_id_fields = ('thread', 'author', 'parent_reply')

@admin.register(Upvote)
class UpvoteAdmin(admin.ModelAdmin):
    list_display = ('user', 'reply', 'created_at')
    list_filter = ('reply__thread__course',)
    search_fields = ('user__email', 'reply__content')
    raw_id_fields = ('user', 'reply')

@admin.register(UserEngagement)
class UserEngagementAdmin(admin.ModelAdmin):
    list_display = ('user', 'engagement_type', 'thread', 'created_at')
    list_filter = ('engagement_type', 'thread__course')
    search_fields = ('user__email', 'thread__title')
    raw_id_fields = ('user', 'thread', 'reply')