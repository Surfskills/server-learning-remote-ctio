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
    is_published = models.BooleanField(default=False)
    allow_multiple_attempts = models.BooleanField(default=False)
    max_attempts = models.PositiveIntegerField(null=True, blank=True)
    time_limit_minutes = models.PositiveIntegerField(null=True, blank=True)
    
    class Meta:
        verbose_name_plural = "Quizzes"
        ordering = ['due_date']
    
    def __str__(self):
        return f"{self.course.title} - {self.title}"

    def clean(self):
        if self.max_attempts is not None and self.max_attempts < 1:
            raise ValidationError("Max attempts must be at least 1")
        if self.time_limit_minutes is not None and self.time_limit_minutes < 1:
            raise ValidationError("Time limit must be at least 1 minute")
                # Validate hierarchy
        if self.lecture and not self.section:
            raise ValidationError("Lecture must belong to a section")
            
        if self.section and self.section.course != self.course:
            raise ValidationError("Section does not belong to course")
            
        if self.lecture and self.lecture.section != self.section:
            raise ValidationError("Lecture does not belong to section")

class QuizQuestion(BaseModel):
    QUESTION_TYPES = [
        ('multiple_choice', 'Multiple Choice'),
        ('true_false', 'True/False'),
        ('short_answer', 'Short Answer'),
        ('essay', 'Essay'),
        ('matching', 'Matching'),
        ('fill_in_blank', 'Fill in the Blank'),
    ]
    
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES, default='multiple_choice')
    question = models.TextField()
    options = JSONField(blank=True, null=True)  # List of strings for multiple choice
    correct_option_index = models.PositiveIntegerField(blank=True, null=True)
    correct_answer = models.TextField(blank=True, null=True)  # For short answer/essay
    points = models.PositiveIntegerField(default=1)
    explanation = models.TextField(blank=True, null=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def clean(self):
        if self.question_type in ['multiple_choice', 'true_false']:
            if not isinstance(self.options, list) or len(self.options) < 2:
                raise ValidationError("Options must be a list with at least 2 items")
            if self.correct_option_index is None:
                raise ValidationError("Correct option index is required")
            if self.correct_option_index >= len(self.options):
                raise ValidationError("Correct option index is out of range")
        elif self.question_type in ['short_answer', 'essay']:
            if not self.correct_answer:
                raise ValidationError("Correct answer is required for this question type")

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
    title = models.CharField(max_length=200)
    description = models.TextField()
    required = models.BooleanField(default=True)
    accepts_files = models.BooleanField(default=False)
    accepted_file_types = JSONField(blank=True, null=True)  # List of SUBMISSION_FILE_TYPE_CHOICES
    max_file_size = models.PositiveIntegerField(blank=True, null=True)  # in bytes
    max_files = models.PositiveIntegerField(blank=True, null=True)
    accepts_text = models.BooleanField(default=False)
    sample_answer = models.TextField(blank=True, null=True)
    points = models.PositiveIntegerField(default=10)
    order = models.PositiveIntegerField(default=0)

    def clean(self):
        if self.accepted_file_types and not isinstance(self.accepted_file_types, list):
            raise ValidationError("Accepted file types must be a list")
        if self.accepted_file_types:
            for file_type in self.accepted_file_types:
                if file_type not in dict(self.SUBMISSION_FILE_TYPE_CHOICES).keys():
                    raise ValidationError(f"Invalid file type: {file_type}")
        if not self.accepts_files and not self.accepts_text:
            raise ValidationError("Task must accept either files or text")

    def __str__(self):
        return f"Task for {self.quiz.title}"

class GradingCriterion(BaseModel):
    task = models.ForeignKey(QuizTask, on_delete=models.CASCADE, related_name='grading_criteria')
    description = models.TextField()
    points = models.PositiveIntegerField()
    order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name_plural = "Grading Criteria"
        ordering = ['order']

    def __str__(self):
        return f"Criterion for {self.task}"

class QuizSubmission(BaseModel):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('graded', 'Graded'),
        ('needs_revision', 'Needs Revision'),
    ]
    
    student = models.ForeignKey('authentication.User', on_delete=models.CASCADE, related_name='quiz_submissions')
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='submissions')
    attempt_number = models.PositiveIntegerField(default=1)
    submitted_at = models.DateTimeField(blank=True, null=True)
    started_at = models.DateTimeField(auto_now_add=True)
    text_response = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    grade = models.FloatField(blank=True, null=True)
    feedback = models.TextField(blank=True, null=True)
    instructor_notes = models.TextField(blank=True, null=True)
    time_spent_seconds = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ['student', 'quiz', 'attempt_number']
        ordering = ['-submitted_at']

    def __str__(self):
        return f"{self.student.email}'s submission for {self.quiz.title}"

class QuestionResponse(BaseModel):
    submission = models.ForeignKey(QuizSubmission, on_delete=models.CASCADE, related_name='question_responses')
    question = models.ForeignKey(QuizQuestion, on_delete=models.CASCADE)
    answer = JSONField(blank=True, null=True)  # Can be text, option index, etc.
    is_correct = models.BooleanField(blank=True, null=True)
    points_awarded = models.FloatField(blank=True, null=True)
    feedback = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Response for question {self.question.id} in submission {self.submission.id}"

class SubmissionFile(BaseModel):
    submission = models.ForeignKey(QuizSubmission, on_delete=models.CASCADE, related_name='files')
    task = models.ForeignKey(QuizTask, on_delete=models.CASCADE, null=True, blank=True)
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
    student = models.ForeignKey('authentication.User', on_delete=models.CASCADE, related_name='quiz_grades')
    overall_score = models.FloatField()
    feedback = models.TextField(blank=True, null=True)
    graded_by = models.ForeignKey(
        'authentication.User', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='graded_quizzes'
    )
    graded_at = models.DateTimeField(auto_now_add=True)
    is_final = models.BooleanField(default=True)

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