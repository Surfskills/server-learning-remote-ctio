from rest_framework import serializers

from courses.models import CourseSection, Lecture
from .models import *
from core.serializers import EmptySerializer

class GradingCriterionSerializer(serializers.ModelSerializer):
    class Meta:
        model = GradingCriterion
        fields = '__all__'

# assessments/serializers.py

class QuizQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuizQuestion
        fields = '__all__'
        read_only_fields = ('quiz',)

class QuizTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuizTask
        fields = '__all__'
        read_only_fields = ('quiz',)

class QuizSerializer(serializers.ModelSerializer):
    questions = QuizQuestionSerializer(many=True, read_only=True)
    tasks = QuizTaskSerializer(many=True, read_only=True)
    
    class Meta:
        model = Quiz
        fields = '__all__'
        extra_kwargs = {
            'course': {'required': True},
            'section': {'required': False},
            'lecture': {'required': False}
        }

class SubmissionFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubmissionFile
        fields = '__all__'

class QuestionResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionResponse
        fields = '__all__'

class QuizSubmissionSerializer(serializers.ModelSerializer):
    files = SubmissionFileSerializer(many=True, read_only=True)
    question_responses = QuestionResponseSerializer(many=True, read_only=True)

    class Meta:
        model = QuizSubmission
        fields = '__all__'
        read_only_fields = ['student', 'attempt_number', 'started_at']

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
    task_grades = TaskGradeSerializer(many=True, read_only=True)

    class Meta:
        model = QuizGrade
        fields = '__all__'