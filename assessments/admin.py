from django.contrib import admin
from .models import (
    Quiz, QuizQuestion, QuizTask, GradingCriterion,
    QuizSubmission, SubmissionFile, QuizGrade,
    TaskGrade, CriteriaGrade
)

@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'section', 'lecture', 'due_date')
    list_filter = ('course', 'section', 'lecture')
    search_fields = ('title', 'description')

@admin.register(QuizQuestion)
class QuizQuestionAdmin(admin.ModelAdmin):
    list_display = ('question', 'quiz', 'correct_option_index')
    list_filter = ('quiz',)
    search_fields = ('question',)

@admin.register(QuizTask)
class QuizTaskAdmin(admin.ModelAdmin):
    list_display = ('question', 'quiz', 'points')
    list_filter = ('quiz',)
    search_fields = ('question', 'description')

@admin.register(GradingCriterion)
class GradingCriterionAdmin(admin.ModelAdmin):
    list_display = ('description', 'task', 'points')
    list_filter = ('task',)
    search_fields = ('description',)

@admin.register(QuizSubmission)
class QuizSubmissionAdmin(admin.ModelAdmin):
    list_display = ('student', 'quiz', 'status', 'grade', 'submitted_at')
    list_filter = ('quiz', 'status', 'student')
    search_fields = ('text_response', 'feedback')

@admin.register(SubmissionFile)
class SubmissionFileAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'submission', 'size')
    list_filter = ('type', 'submission')
    search_fields = ('name',)

@admin.register(QuizGrade)
class QuizGradeAdmin(admin.ModelAdmin):
    list_display = ('student', 'quiz', 'overall_score', 'graded_by', 'graded_at')
    list_filter = ('quiz', 'student', 'graded_by')
    search_fields = ('feedback',)

@admin.register(TaskGrade)
class TaskGradeAdmin(admin.ModelAdmin):
    list_display = ('grade', 'task', 'score')
    list_filter = ('grade', 'task')
    search_fields = ('feedback',)

@admin.register(CriteriaGrade)
class CriteriaGradeAdmin(admin.ModelAdmin):
    list_display = ('task_grade', 'criterion', 'awarded_points')
    list_filter = ('task_grade', 'criterion')
    search_fields = ('comments',)