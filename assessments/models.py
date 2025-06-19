from django.db import models
from django.core.exceptions import ValidationError
from django.db.models import JSONField
import uuid
from core.models import BaseModel

class Quiz(BaseModel):
    course = models.ForeignKey('courses.Course', on_delete=models.CASCADE, related_name='quizzes')

    section = models.ForeignKey('courses.CourseSection', on_delete=models.SET_NULL, null=True, blank=True, related_name='quizzes')
    lecture = models.ForeignKey('courses.Lecture', on_delete=models.SET_NULL, null=True, blank=True, related_name='quizzes')
    title = models.CharField(max_length=200)
    description = models.TextField()
    instructions = models.TextField()
    due_date = models.DateTimeField(blank=True, null=True)
    points_possible = models.PositiveIntegerField(default=10)
    
    class Meta:
        verbose_name_plural = "Quizzes"
        ordering = ['due_date']
    
    def __str__(self):
        return f"{self.course.title} - {self.title}"


class QuizQuestion(BaseModel):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    question = models.TextField()
    options = JSONField()  # List of strings
    correct_option_index = models.PositiveIntegerField()

    class Meta:
        ordering = ['created_at']

    def clean(self):
        if not isinstance(self.options, list):
            raise ValidationError("Options must be a list of strings")
        if self.correct_option_index >= len(self.options):
            raise ValidationError("Correct option index is out of range")

    def __str__(self):
        return f"Question for {self.quiz.title}"

class QuizTask(BaseModel):
    SUBMISSION_FILE_TYPE_CHOICES = [
        ('video', 'Video'),
        ('pdf', 'PDF'),
        ('image', 'Image'),
        ('audio', 'Audio'),
        ('document', 'Document'),
        ('code', 'Code'),
    ]
    
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='tasks')
    question = models.TextField()
    description = models.TextField(blank=True, null=True)
    required = models.BooleanField(default=True)
    accepts_files = models.BooleanField(default=False)
    accepted_file_types = models.JSONField(blank=True, null=True)  # List of SUBMISSION_FILE_TYPE_CHOICES
    max_file_size = models.PositiveIntegerField(blank=True, null=True)  # in bytes
    max_files = models.PositiveIntegerField(blank=True, null=True)
    accepts_text = models.BooleanField(default=False)
    sample_answer = models.TextField(blank=True, null=True)
    points = models.PositiveIntegerField(default=10)

    def clean(self):
        if self.accepted_file_types and not isinstance(self.accepted_file_types, list):
            raise ValidationError("Accepted file types must be a list")
        if self.accepted_file_types:
            for file_type in self.accepted_file_types:
                if file_type not in dict(self.SUBMISSION_FILE_TYPE_CHOICES).keys():
                    raise ValidationError(f"Invalid file type: {file_type}")

    def __str__(self):
        return f"Task for {self.quiz.title}"

class GradingCriterion(BaseModel):
    task = models.ForeignKey(QuizTask, on_delete=models.CASCADE, related_name='grading_criteria')
    description = models.TextField()
    points = models.PositiveIntegerField()

    class Meta:
        verbose_name_plural = "Grading Criteria"

    def __str__(self):
        return f"Criterion for {self.task}"

class QuizSubmission(BaseModel):
    STATUS_CHOICES = [
        ('submitted', 'Submitted'),
        ('graded', 'Graded'),
        ('needs_revision', 'Needs Revision'),
    ]
    
    student = models.ForeignKey(
        'authentication.User', 
        on_delete=models.CASCADE, 
        related_name='assessments_quiz_submissions'  # Changed
    )
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='submissions')
    submitted_at = models.DateTimeField(auto_now_add=True)
    text_response = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='submitted')
    grade = models.FloatField(blank=True, null=True)
    feedback = models.TextField(blank=True, null=True)
    instructor_notes = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ['student', 'quiz']
        ordering = ['-submitted_at']

    def __str__(self):
        return f"{self.student.email}'s submission for {self.quiz.title}"

class SubmissionFile(BaseModel):
    submission = models.ForeignKey(QuizSubmission, on_delete=models.CASCADE, related_name='files')
    url = models.URLField(max_length=500)
    type = models.CharField(max_length=10, choices=QuizTask.SUBMISSION_FILE_TYPE_CHOICES)
    name = models.CharField(max_length=200)
    size = models.PositiveIntegerField()  # in bytes
    mime_type = models.CharField(max_length=100)
    thumbnail_url = models.URLField(max_length=500, blank=True, null=True)
    duration = models.PositiveIntegerField(blank=True, null=True)  # in seconds

    def __str__(self):
        return f"File for {self.submission}"

class QuizGrade(BaseModel):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='grades')
    student = models.ForeignKey(
        'authentication.User', 
        on_delete=models.CASCADE, 
        related_name='assessments_quiz_grades'  # Changed
    )
    overall_score = models.FloatField()
    feedback = models.TextField(blank=True, null=True)
    graded_by = models.ForeignKey(
        'authentication.User', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='assessments_graded_quizzes'  # Changed
    )
    graded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['quiz', 'student']
        ordering = ['-graded_at']

    def __str__(self):
        return f"Grade for {self.student.email} on {self.quiz.title}"

class TaskGrade(BaseModel):
    grade = models.ForeignKey(QuizGrade, on_delete=models.CASCADE, related_name='task_grades')
    task = models.ForeignKey(QuizTask, on_delete=models.CASCADE, related_name='grades')
    score = models.FloatField()
    feedback = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Task grade for {self.grade}"

class CriteriaGrade(BaseModel):
    task_grade = models.ForeignKey(TaskGrade, on_delete=models.CASCADE, related_name='criteria_grades')
    criterion = models.ForeignKey(GradingCriterion, on_delete=models.CASCADE, related_name='grades')
    awarded_points = models.PositiveIntegerField()
    comments = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Criteria grade for {self.task_grade}"