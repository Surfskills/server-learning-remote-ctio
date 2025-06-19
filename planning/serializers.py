# serializers.py
from rest_framework import serializers

from .models import (
    CalendarEvent, 
    CalendarNotification,

    CalendarPermissions,
    PlannedCourseRelease,
    StudentProgressControl,
    DripSchedule,
    DripScheduleEntry
)
from authentication.serializers import UserSerializer
from courses.serializers import CourseSectionSerializer, CourseSerializer, LectureSerializer

class CalendarEventSerializer(serializers.ModelSerializer):
    course = CourseSerializer(read_only=True)
    related_lecture = LectureSerializer(read_only=True)
    attendees = UserSerializer(many=True, read_only=True)
    created_by = UserSerializer(read_only=True)

    class Meta:
        model = CalendarEvent
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']

class CalendarNotificationSerializer(serializers.ModelSerializer):
    event = CalendarEventSerializer(read_only=True)
    user = UserSerializer(read_only=True)

    class Meta:
        model = CalendarNotification
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class CalendarPermissionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = CalendarPermissions
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']

class PlannedCourseReleaseSerializer(serializers.ModelSerializer):
    course = CourseSerializer(read_only=True)
    student = UserSerializer(read_only=True)
    section = CourseSectionSerializer(read_only=True)
    lecture = LectureSerializer(read_only=True)
    related_event = CalendarEventSerializer(read_only=True)

    class Meta:
        model = PlannedCourseRelease
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']

class StudentProgressControlSerializer(serializers.ModelSerializer):
    student = UserSerializer(read_only=True)
    course = CourseSerializer(read_only=True)
    locked_lectures = LectureSerializer(many=True, read_only=True)
    unlocked_lectures = LectureSerializer(many=True, read_only=True)

    class Meta:
        model = StudentProgressControl
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']

class DripScheduleEntrySerializer(serializers.ModelSerializer):
    section = CourseSectionSerializer(read_only=True)
    lecture = LectureSerializer(read_only=True)

    class Meta:
        model = DripScheduleEntry
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']

class DripScheduleSerializer(serializers.ModelSerializer):
    entries = DripScheduleEntrySerializer(many=True, read_only=True)

    class Meta:
        model = DripSchedule
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']