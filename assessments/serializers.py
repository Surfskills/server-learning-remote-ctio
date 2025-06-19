from rest_framework import serializers
from .models import *
from core.serializers import EmptySerializer

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
    task_grades = TaskGradeSerializer(many=True, read_only=True)

    class Meta:
        model = QuizGrade
        fields = '__all__'