from rest_framework import serializers
from .models import *
from django.contrib.auth import get_user_model

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'user_type', 'is_active', 'profile_picture']
        read_only_fields = ['id', 'user_type', 'is_active']

class CourseCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseCategory
        fields = '__all__'

class InstructorSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'profile_picture']

class CourseSerializer(serializers.ModelSerializer):
    instructor = InstructorSerializer(read_only=True)
    category = CourseCategorySerializer(read_only=True)
    current_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    is_enrolled = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = '__all__'

    def get_is_enrolled(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.enrollments.filter(student=request.user).exists()
        return False

class CourseSectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseSection
        fields = '__all__'

class LectureResourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LectureResource
        fields = '__all__'

class QaItemSerializer(serializers.ModelSerializer):
    asked_by = UserSerializer(read_only=True)

    class Meta:
        model = QaItem
        fields = '__all__'

class ProjectToolSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectTool
        fields = '__all__'

class LectureSerializer(serializers.ModelSerializer):
    resources = LectureResourceSerializer(many=True, read_only=True)
    qa_items = QaItemSerializer(many=True, read_only=True)
    project_tools = ProjectToolSerializer(many=True, read_only=True)
    is_completed = serializers.SerializerMethodField()

    class Meta:
        model = Lecture
        fields = '__all__'

    def get_is_completed(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            enrollment = Enrollment.objects.filter(
                student=request.user,
                course=obj.section.course
            ).first()
            if enrollment and hasattr(enrollment, 'progress'):
                return enrollment.progress.completed_lectures.filter(id=obj.id).exists()
        return False

class EnrollmentSerializer(serializers.ModelSerializer):
    student = UserSerializer(read_only=True)
    course = CourseSerializer(read_only=True)

    class Meta:
        model = Enrollment
        fields = '__all__'

class CourseProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseProgress
        fields = '__all__'

class ReviewSerializer(serializers.ModelSerializer):
    student = UserSerializer(read_only=True)

    class Meta:
        model = Review
        fields = '__all__'

class QuizQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuizQuestion
        fields = '__all__'

class GradingCriterionSerializer(serializers.ModelSerializer):
    class Meta:
        model = GradingCriterion
        fields = '__all__'

class QuizTaskSerializer(serializers.ModelSerializer):
    grading_criteria = GradingCriterionSerializer(many=True, read_only=True)

    class Meta:
        model = QuizTask
        fields = '__all__'

class QuizSerializer(serializers.ModelSerializer):
    questions = QuizQuestionSerializer(many=True, read_only=True)
    tasks = QuizTaskSerializer(many=True, read_only=True)

    class Meta:
        model = Quiz
        fields = '__all__'

class SubmissionFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubmissionFile
        fields = '__all__'

class QuizSubmissionSerializer(serializers.ModelSerializer):
    student = UserSerializer(read_only=True)
    files = SubmissionFileSerializer(many=True, read_only=True)

    class Meta:
        model = QuizSubmission
        fields = '__all__'

class CriteriaGradeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CriteriaGrade
        fields = '__all__'

class TaskGradeSerializer(serializers.ModelSerializer):
    criteria_grades = CriteriaGradeSerializer(many=True, read_only=True)

    class Meta:
        model = TaskGrade
        fields = '__all__'

class QuizGradeSerializer(serializers.ModelSerializer):
    student = UserSerializer(read_only=True)
    graded_by = UserSerializer(read_only=True)
    task_grades = TaskGradeSerializer(many=True, read_only=True)

    class Meta:
        model = QuizGrade
        fields = '__all__'

class OrderSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    course = CourseSerializer(read_only=True)

    class Meta:
        model = Order
        fields = '__all__'

class CertificateSerializer(serializers.ModelSerializer):
    student = UserSerializer(read_only=True)
    course = CourseSerializer(read_only=True)

    class Meta:
        model = Certificate
        fields = '__all__'

class FaqSerializer(serializers.ModelSerializer):
    class Meta:
        model = Faq
        fields = '__all__'

class AnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Announcement
        fields = '__all__'

class CalendarEventSerializer(serializers.ModelSerializer):
    course = CourseSerializer(read_only=True)
    related_lecture = LectureSerializer(read_only=True)
    attendees = UserSerializer(many=True, read_only=True)
    created_by = UserSerializer(read_only=True)

    class Meta:
        model = CalendarEvent
        fields = '__all__'

class CalendarNotificationSerializer(serializers.ModelSerializer):
    event = CalendarEventSerializer(read_only=True)
    user = UserSerializer(read_only=True)

    class Meta:
        model = CalendarNotification
        fields = '__all__'

class NotificationPreferencesSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreferences
        fields = '__all__'

class CalendarPermissionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = CalendarPermissions
        fields = '__all__'

class PlannedCourseReleaseSerializer(serializers.ModelSerializer):
    course = CourseSerializer(read_only=True)
    student = UserSerializer(read_only=True)
    section = CourseSectionSerializer(read_only=True)
    lecture = LectureSerializer(read_only=True)
    related_event = CalendarEventSerializer(read_only=True)

    class Meta:
        model = PlannedCourseRelease
        fields = '__all__'

class StudentProgressControlSerializer(serializers.ModelSerializer):
    student = UserSerializer(read_only=True)
    course = CourseSerializer(read_only=True)
    locked_lectures = LectureSerializer(many=True, read_only=True)
    unlocked_lectures = LectureSerializer(many=True, read_only=True)

    class Meta:
        model = StudentProgressControl
        fields = '__all__'

class DripScheduleEntrySerializer(serializers.ModelSerializer):
    section = CourseSectionSerializer(read_only=True)
    lecture = LectureSerializer(read_only=True)

    class Meta:
        model = DripScheduleEntry
        fields = '__all__'

class DripScheduleSerializer(serializers.ModelSerializer):
    entries = DripScheduleEntrySerializer(many=True, read_only=True)

    class Meta:
        model = DripSchedule
        fields = '__all__'