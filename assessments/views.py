
from rest_framework.permissions import IsAuthenticated
from core.views import BaseModelViewSet
from core.permissions import IsInstructor, IsStudent, IsCourseInstructor, IsEnrolledStudent
from .models import (
    Quiz, QuizQuestion, QuizTask, GradingCriterion,
    QuizSubmission, SubmissionFile, QuizGrade,
    TaskGrade, CriteriaGrade
)
from .serializers import (
    QuizSerializer, QuizQuestionSerializer,
    QuizTaskSerializer, GradingCriterionSerializer,
    QuizSubmissionSerializer, SubmissionFileSerializer,
    QuizGradeSerializer, TaskGradeSerializer,
    CriteriaGradeSerializer
)

class QuizViewSet(BaseModelViewSet):
    queryset = Quiz.objects.all()
    serializer_class = QuizSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        course_id = self.request.query_params.get('course_id')
        if course_id:
            queryset = queryset.filter(course_id=course_id)
        return queryset

class QuizQuestionViewSet(BaseModelViewSet):
    queryset = QuizQuestion.objects.all()
    serializer_class = QuizQuestionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        quiz_id = self.request.query_params.get('quiz_id')
        if quiz_id:
            queryset = queryset.filter(quiz_id=quiz_id)
        return queryset

class QuizTaskViewSet(BaseModelViewSet):
    queryset = QuizTask.objects.all()
    serializer_class = QuizTaskSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        quiz_id = self.request.query_params.get('quiz_id')
        if quiz_id:
            queryset = queryset.filter(quiz_id=quiz_id)
        return queryset

class GradingCriterionViewSet(BaseModelViewSet):
    queryset = GradingCriterion.objects.all()
    serializer_class = GradingCriterionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        task_id = self.request.query_params.get('task_id')
        if task_id:
            queryset = queryset.filter(task_id=task_id)
        return queryset

class QuizSubmissionViewSet(BaseModelViewSet):
    queryset = QuizSubmission.objects.all()
    serializer_class = QuizSubmissionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        quiz_id = self.request.query_params.get('quiz_id')
        if quiz_id:
            queryset = queryset.filter(quiz_id=quiz_id)
        if not self.request.user.is_staff:
            queryset = queryset.filter(student=self.request.user)
        return queryset

    def perform_create(self, serializer):
        serializer.save(student=self.request.user)

class SubmissionFileViewSet(BaseModelViewSet):
    queryset = SubmissionFile.objects.all()
    serializer_class = SubmissionFileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        submission_id = self.request.query_params.get('submission_id')
        if submission_id:
            queryset = queryset.filter(submission_id=submission_id)
        return queryset

class QuizGradeViewSet(BaseModelViewSet):
    queryset = QuizGrade.objects.all()
    serializer_class = QuizGradeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        quiz_id = self.request.query_params.get('quiz_id')
        if quiz_id:
            queryset = queryset.filter(quiz_id=quiz_id)
        if not self.request.user.is_staff:
            queryset = queryset.filter(student=self.request.user)
        return queryset

class TaskGradeViewSet(BaseModelViewSet):
    queryset = TaskGrade.objects.all()
    serializer_class = TaskGradeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        grade_id = self.request.query_params.get('grade_id')
        if grade_id:
            queryset = queryset.filter(grade_id=grade_id)
        return queryset

class CriteriaGradeViewSet(BaseModelViewSet):
    queryset = CriteriaGrade.objects.all()
    serializer_class = CriteriaGradeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        task_grade_id = self.request.query_params.get('task_grade_id')
        if task_grade_id:
            queryset = queryset.filter(task_grade_id=task_grade_id)
        return queryset