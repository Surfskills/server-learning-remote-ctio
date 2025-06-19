from rest_framework import serializers

from .models import DiscussionThread, ThreadReply, Upvote, UserEngagement
from authentication.models import User
from courses.serializers import CourseSerializer, LectureSerializer

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'profile_picture']
        read_only_fields = fields

class ThreadReplySerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    is_upvoted = serializers.SerializerMethodField()
    child_replies = serializers.SerializerMethodField()

    class Meta:
        model = ThreadReply
        fields = '__all__'
        read_only_fields = ['thread', 'author', 'upvotes']

    def get_is_upvoted(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.upvote_instances.filter(user=request.user).exists()
        return False

    def get_child_replies(self, obj):
        serializer = ThreadReplySerializer(
            obj.child_replies.all(),
            many=True,
            context=self.context
        )
        return serializer.data

class DiscussionThreadSerializer(serializers.ModelSerializer):
    started_by = UserSerializer(read_only=True)
    course = CourseSerializer(read_only=True)
    lecture = LectureSerializer(read_only=True)
    reply_count = serializers.IntegerField(source='replies.count', read_only=True)
    latest_reply = serializers.SerializerMethodField()
    is_following = serializers.SerializerMethodField()

    class Meta:
        model = DiscussionThread
        fields = '__all__'
        read_only_fields = ['started_by', 'view_count']

    def get_latest_reply(self, obj):
        latest = obj.replies.order_by('-created_at').first()
        if latest:
            return ThreadReplySerializer(latest, context=self.context).data
        return None

    def get_is_following(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.engagements.filter(
                user=request.user,
                engagement_type='follow'
            ).exists()
        return False

class UpvoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Upvote
        fields = '__all__'
        read_only_fields = ['user']

class UserEngagementSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserEngagement
        fields = '__all__'
        read_only_fields = ['user']

class CreateThreadSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiscussionThread
        fields = ['title', 'content', 'thread_type', 'lecture']
        extra_kwargs = {
            'lecture': {'required': False}
        }

    def validate(self, data):
        if data.get('lecture') and data['lecture'].course != self.context['course']:
            raise serializers.ValidationError("Lecture does not belong to this course")
        return data

    def create(self, validated_data):
        validated_data['started_by'] = self.context['request'].user
        validated_data['course'] = self.context['course']
        return super().create(validated_data)