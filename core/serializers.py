from rest_framework import serializers
from .models import HealthCheck
from django.db.models import Count

class HealthCheckSerializer(serializers.ModelSerializer):
    class Meta:
        model = HealthCheck
        fields = '__all__'
        read_only_fields = ['last_checked']

class EmptySerializer(serializers.Serializer):
    """
    Empty serializer for actions that don't need input
    """
    pass

# serializers.py
from rest_framework import serializers
from enrollments.models import Enrollment, CourseProgress
from courses.models import Course
from users.models import UserActivity

class DashboardCourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ['id', 'title', 'slug', 'banner_url', 'duration', 'description', 'level']

class DashboardProgressSerializer(serializers.ModelSerializer):
    progress_percentage = serializers.SerializerMethodField()
    total_lectures = serializers.SerializerMethodField()
    completed_lectures_count = serializers.SerializerMethodField()

    class Meta:
        model = CourseProgress
        fields = ['id', 'progress_percentage', 'total_lectures', 'completed_lectures_count', 'last_accessed']

    def get_progress_percentage(self, obj):
        course = obj.enrollment.course
        total_lectures = course.sections.aggregate(total=Count('lectures'))['total'] or 0
        if total_lectures == 0:
            return 0
        return round((obj.completed_lectures.count() / total_lectures) * 100)

    def get_total_lectures(self, obj):
        course = obj.enrollment.course
        return course.sections.aggregate(total=Count('lectures'))['total'] or 0

    def get_completed_lectures_count(self, obj):
        return obj.completed_lectures.count()

class DashboardEnrollmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Enrollment
        fields = ['id', 'enrolled_at', 'completed', 'last_accessed']

class UserActivitySerializer(serializers.ModelSerializer):
    course_title = serializers.SerializerMethodField()
    activity_type = serializers.SerializerMethodField()
    title = serializers.SerializerMethodField()

    class Meta:
        model = UserActivity
        fields = ['id', 'activity_type', 'title', 'course_title', 'created_at']

    def get_course_title(self, obj):
        # Extract course title from activity details if available
        return obj.details.get('course_title', 'Unknown Course')

    def get_activity_type(self, obj):
        # Map activity types to simpler values
        activity_map = {
            'lecture_viewed': 'lecture',
            'quiz_completed': 'quiz',
            'resource_viewed': 'resource'
        }
        return activity_map.get(obj.activity_type, 'activity')

    def get_title(self, obj):
        # Extract title from activity details
        return obj.details.get('title', 'Activity')