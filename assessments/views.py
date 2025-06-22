# assessments/views.py
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.db import transaction
from core.views import BaseModelViewSet
from core.permissions import IsCourseInstructor
from .models import *
from .serializers import *
from django.core.exceptions import PermissionDenied
class QuizViewSet(BaseModelViewSet):
    queryset = Quiz.objects.all()
    serializer_class = QuizSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        course_id = self.request.query_params.get('course_id')
        section_id = self.request.query_params.get('section_id')
        lecture_id = self.request.query_params.get('lecture_id')
        
        if course_id:
            queryset = queryset.filter(course_id=course_id)
        if section_id:
            queryset = queryset.filter(section_id=section_id)
        if lecture_id:
            queryset = queryset.filter(lecture_id=lecture_id)
            
        # Students can only see published quizzes
        if not self.request.user.is_staff and not self.request.user.is_instructor:
            queryset = queryset.filter(is_published=True)
            
        return queryset

    def perform_create(self, serializer):
        # Ensure the user has permission to create quizzes for this course
        course_id = serializer.validated_data.get('course_id')
        if not IsCourseInstructor().has_object_permission(self.request, self, course_id):
            raise PermissionDenied("You don't have permission to create quizzes for this course")
        serializer.save()

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        quiz = self.get_object()
        quiz.is_published = True
        quiz.save()
        return Response({'status': 'published'})

    @action(detail=True, methods=['post'])
    def unpublish(self, request, pk=None):
        quiz = self.get_object()
        quiz.is_published = False
        quiz.save()
        return Response({'status': 'unpublished'})

class QuizQuestionViewSet(BaseModelViewSet):
    queryset = QuizQuestion.objects.all()
    serializer_class = QuizQuestionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        quiz_id = self.request.query_params.get('quiz_id')
        lecture_id = self.request.query_params.get('lecture_id')
        
        if quiz_id:
            queryset = queryset.filter(quiz_id=quiz_id)
        if lecture_id:
            queryset = queryset.filter(quiz__lecture_id=lecture_id)
        return queryset

    def perform_create(self, serializer):
        quiz = serializer.validated_data['quiz']
        if not IsCourseInstructor().has_object_permission(self.request, self, quiz.course_id):
            raise PermissionDenied("You don't have permission to add questions to this quiz")
        serializer.save()

class QuizTaskViewSet(BaseModelViewSet):
    queryset = QuizTask.objects.all()
    serializer_class = QuizTaskSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        quiz_id = self.request.query_params.get('quiz_id')
        lecture_id = self.request.query_params.get('lecture_id')
        
        if quiz_id:
            queryset = queryset.filter(quiz_id=quiz_id)
        if lecture_id:
            queryset = queryset.filter(quiz__lecture_id=lecture_id)
        return queryset

    def perform_create(self, serializer):
        quiz = serializer.validated_data['quiz']
        if not IsCourseInstructor().has_object_permission(self.request, self, quiz.course_id):
            raise PermissionDenied("You don't have permission to add tasks to this quiz")
        serializer.save()


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
        quiz = serializer.validated_data['quiz']
        
        # Calculate attempt number
        last_submission = QuizSubmission.objects.filter(
            student=self.request.user,
            quiz=quiz
        ).order_by('-attempt_number').first()
        
        attempt_number = 1
        if last_submission:
            attempt_number = last_submission.attempt_number + 1
            
        # Check if max attempts reached
        if quiz.max_attempts and attempt_number > quiz.max_attempts:
            raise serializers.ValidationError("Maximum number of attempts reached for this quiz")
            
        serializer.save(student=self.request.user, attempt_number=attempt_number)

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        submission = self.get_object()
        
        if submission.status != 'draft':
            return Response(
                {'error': 'Submission has already been submitted'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Calculate time spent if quiz has time limit
        if submission.quiz.time_limit_minutes:
            time_spent = (timezone.now() - submission.started_at).total_seconds()
            submission.time_spent_seconds = min(time_spent, submission.quiz.time_limit_minutes * 60)
        
        submission.status = 'submitted'
        submission.submitted_at = timezone.now()
        submission.save()
        
        return Response({'status': 'submitted'})

    @action(detail=True, methods=['post'])
    def auto_grade(self, request, pk=None):
        submission = self.get_object()
        
        if submission.status != 'submitted':
            return Response(
                {'error': 'Only submitted submissions can be graded'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Auto-grade multiple choice questions
        total_points = 0
        possible_points = 0
        
        for response in submission.question_responses.all():
            question = response.question
            
            if question.question_type in ['multiple_choice', 'true_false']:
                response.is_correct = (response.answer == question.correct_option_index)
                if response.is_correct:
                    response.points_awarded = question.points
                else:
                    response.points_awarded = 0
                response.save()
            
            if question.question_type in ['short_answer'] and question.correct_answer:
                # Simple exact match for short answer
                response.is_correct = (str(response.answer).strip().lower() == str(question.correct_answer).strip().lower())
                if response.is_correct:
                    response.points_awarded = question.points
                else:
                    response.points_awarded = 0
                response.save()
            
            if hasattr(response, 'points_awarded'):
                total_points += response.points_awarded
            possible_points += question.points
        
        # Calculate percentage score
        if possible_points > 0:
            percentage_score = (total_points / possible_points) * 100
        else:
            percentage_score = 0
            
        # Create or update grade
        grade, created = QuizGrade.objects.update_or_create(
            quiz=submission.quiz,
            student=submission.student,
            defaults={
                'overall_score': percentage_score,
                'graded_by': request.user if request.user.is_staff else None,
                'is_final': False
            }
        )
        
        submission.grade = percentage_score
        submission.status = 'graded'
        submission.save()
        
        return Response({'status': 'graded', 'score': percentage_score})

class QuestionResponseViewSet(BaseModelViewSet):
    queryset = QuestionResponse.objects.all()
    serializer_class = QuestionResponseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        submission_id = self.request.query_params.get('submission_id')
        if submission_id:
            queryset = queryset.filter(submission_id=submission_id)
        return queryset

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