# enrollments/models.py
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from core.models import BaseModel
from authentication.models import User
from courses.models import Course

class Enrollment(BaseModel):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='enrollments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')
    enrolled_at = models.DateTimeField(auto_now_add=True)
    completed = models.BooleanField(default=False)
    progress_percentage = models.FloatField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    last_accessed = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['student', 'course']
        ordering = ['-enrolled_at']

    def __str__(self):
        return f"{self.student.email} enrolled in {self.course.title}"

class CourseProgress(BaseModel):
    # Fixed: Remove primary_key=True since BaseModel already provides primary key
    enrollment = models.OneToOneField(
        Enrollment,
        on_delete=models.CASCADE,
        related_name='progress'
    )
    # Fixed: Use string reference to avoid import issues
    completed_lectures = models.ManyToManyField('courses.Lecture', blank=True)
    last_accessed_lecture = models.ForeignKey(
        'courses.Lecture',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+'
    )

    @property
    def progress_percentage(self):
        # Get all lectures through sections
        total_lectures = 0
        for section in self.enrollment.course.sections.all():
            total_lectures += section.lectures.count()
        
        if total_lectures == 0:
            return 0
        completed_count = self.completed_lectures.count()
        return (completed_count / total_lectures) * 100

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update the progress percentage in the enrollment
        self.enrollment.progress_percentage = self.progress_percentage
        self.enrollment.save()

    def __str__(self):
        return f"Progress for {self.enrollment}"

