from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from .models import DiscussionThread, ThreadReply, Upvote, UserEngagement
from .serializers import (
    DiscussionThreadSerializer,
    ThreadReplySerializer,
    UpvoteSerializer,
    UserEngagementSerializer,
    CreateThreadSerializer
)
from core.views import BaseModelViewSet
from core.utils import success_response, error_response
from core.permissions import IsCourseEnrolled
from courses.models import Course

class DiscussionThreadViewSet(BaseModelViewSet):
    serializer_class = DiscussionThreadSerializer
    permission_classes = [IsAuthenticated, IsCourseEnrolled]
    filterset_fields = ['thread_type', 'is_pinned', 'is_closed']
    search_fields = ['title', 'content']

    def get_queryset(self):
        course_id = self.kwargs.get('course_pk')
        return DiscussionThread.objects.filter(
            course_id=course_id
        ).select_related(
            'started_by', 'course', 'lecture'
        ).prefetch_related(
            'replies'
        ).order_by('-is_pinned', '-created_at')

    def get_serializer_class(self):
        if self.action == 'create':
            return CreateThreadSerializer
        return super().get_serializer_class()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['course'] = Course.objects.get(pk=self.kwargs.get('course_pk'))
        return context

    @action(detail=True, methods=['post'])
    def pin(self, request, pk=None, course_pk=None):
        thread = self.get_object()
        thread.is_pinned = not thread.is_pinned
        thread.save()
        action = "pinned" if thread.is_pinned else "unpinned"
        return success_response(f"Thread {action} successfully")

    @action(detail=True, methods=['post'])
    def close(self, request, pk=None, course_pk=None):
        thread = self.get_object()
        thread.is_closed = not thread.is_closed
        thread.save()
        action = "closed" if thread.is_closed else "reopened"
        return success_response(f"Thread {action} successfully")

    @action(detail=True, methods=['post'])
    def follow(self, request, pk=None, course_pk=None):
        thread = self.get_object()
        engagement, created = UserEngagement.objects.get_or_create(
            user=request.user,
            thread=thread,
            engagement_type='follow',
            defaults={'metadata': {}}
        )
        
        if not created:
            engagement.delete()
            return success_response("Thread unfollowed")
        return success_response("Thread followed")

class ThreadReplyViewSet(BaseModelViewSet):
    serializer_class = ThreadReplySerializer
    permission_classes = [IsAuthenticated, IsCourseEnrolled]

    def get_queryset(self):
        thread_id = self.kwargs.get('thread_pk')
        return ThreadReply.objects.filter(
            thread_id=thread_id
        ).select_related(
            'author', 'thread'
        ).prefetch_related(
            'child_replies'
        ).order_by('created_at')

    def perform_create(self, serializer):
        thread = DiscussionThread.objects.get(pk=self.kwargs.get('thread_pk'))
        serializer.save(author=self.request.user, thread=thread)

    @action(detail=True, methods=['post'])
    def mark_as_answer(self, request, pk=None, thread_pk=None):
        reply = self.get_object()
        
        # Clear previous answer if exists
        ThreadReply.objects.filter(
            thread=reply.thread,
            is_answer=True
        ).update(is_answer=False)
        
        reply.is_answer = True
        reply.save()
        return success_response("Marked as answer")

class UpvoteViewSet(BaseModelViewSet):
    serializer_class = UpvoteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Upvote.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        reply_id = request.data.get('reply')
        if not reply_id:
            return error_response("Reply ID is required", status_code=status.HTTP_400_BAD_REQUEST)
        
        reply = ThreadReply.objects.get(pk=reply_id)
        upvote, created = Upvote.objects.get_or_create(
            user=request.user,
            reply=reply
        )
        
        if not created:
            upvote.delete()
            reply.upvotes = max(0, reply.upvotes - 1)
            action = "removed"
        else:
            reply.upvotes += 1
            action = "added"
        
        reply.save()
        return success_response(f"Upvote {action} successfully")

class UserEngagementViewSet(BaseModelViewSet):
    serializer_class = UserEngagementSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return UserEngagement.objects.filter(user=self.request.user)