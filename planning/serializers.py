from rest_framework import serializers
from .models import (
    CalendarEvent, CalendarNotification, UserCalendarSettings,
    ContentReleaseSchedule, ContentReleaseRule, StudentProgressOverride
)
from authentication.serializers import UserSerializer
from courses.serializers import (
    CourseSerializer, CourseSectionSerializer, LectureSerializer,
    QuizSerializer
)

class CalendarEventSerializer(serializers.ModelSerializer):
    course = CourseSerializer(read_only=True)
    section = CourseSectionSerializer(read_only=True)
    lecture = LectureSerializer(read_only=True)
    attendees = UserSerializer(many=True, read_only=True)
    created_by = UserSerializer(read_only=True)
    
    course_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    section_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    lecture_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    attendee_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False,
        default=list
    )

    class Meta:
        model = CalendarEvent
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']

    def validate(self, data):
        event_type = data.get('event_type')
        course_event_type = data.get('course_event_type')
        
        if event_type == 'course' and not course_event_type:
            raise serializers.ValidationError(
                "course_event_type is required for course events"
            )
        
        return data

    def create(self, validated_data):
        attendee_ids = validated_data.pop('attendee_ids', [])
        event = super().create(validated_data)
        
        if attendee_ids:
            event.attendees.set(attendee_ids)
        
        return event

class CalendarNotificationSerializer(serializers.ModelSerializer):
    event = CalendarEventSerializer(read_only=True)
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = CalendarNotification
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'sent', 'sent_at']

class UserCalendarSettingsSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = UserCalendarSettings
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']



class ContentReleaseScheduleSerializer(serializers.ModelSerializer):
    course = CourseSerializer(read_only=True)
    course_id = serializers.UUIDField(write_only=True)
    created_by = UserSerializer(read_only=True)
    
    class Meta:
        model = ContentReleaseSchedule
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'created_by']

class ContentReleaseRuleSerializer(serializers.ModelSerializer):
    schedule = ContentReleaseScheduleSerializer(read_only=True)
    section = CourseSectionSerializer(read_only=True)
    lecture = LectureSerializer(read_only=True)
    quiz = QuizSerializer(read_only=True)

    release_event = CalendarEventSerializer(read_only=True)
    
    schedule_id = serializers.UUIDField(write_only=True)
    section_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    lecture_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    quiz_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
  

    class Meta:
        model = ContentReleaseRule
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'is_released']

class StudentProgressOverrideSerializer(serializers.ModelSerializer):
    student = UserSerializer(read_only=True)
    rule = ContentReleaseRuleSerializer(read_only=True)
    
    student_id = serializers.UUIDField(write_only=True)
    rule_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = StudentProgressOverride
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']