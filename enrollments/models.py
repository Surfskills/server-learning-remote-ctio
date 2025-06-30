# enrollments/models.py
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models.signals import m2m_changed
from django.dispatch import receiver
from core.models import BaseModel
from authentication.models import User

class Enrollment(BaseModel):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='enrollments')
    course = models.ForeignKey('courses.Course', on_delete=models.CASCADE, related_name='enrollments')
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

    def update_progress_percentage(self):
        """Update progress percentage based on completed lectures"""
        try:
            progress = self.progress
            # Calculate total lectures in the course
            total_lectures = 0
            for section in self.course.sections.all():
                total_lectures += section.lectures.count()
            
            if total_lectures == 0:
                self.progress_percentage = 0
            else:
                completed_count = progress.completed_lectures.count()
                self.progress_percentage = round((completed_count / total_lectures) * 100, 2)
            
            self.save(update_fields=['progress_percentage'])
        except CourseProgress.DoesNotExist:
            self.progress_percentage = 0
            self.save(update_fields=['progress_percentage'])

class CourseProgress(BaseModel):
    enrollment = models.OneToOneField(
        Enrollment,
        on_delete=models.CASCADE,
        related_name='progress'
    )
    completed_lectures = models.ManyToManyField('courses.Lecture', blank=True)
    last_accessed_lecture = models.ForeignKey(
        'courses.Lecture',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+'
    )

    def __str__(self):
        return f"Progress for {self.enrollment}"

    def get_progress_stats(self):
        """Get detailed progress statistics"""
        # Calculate total lectures in the course
        total_lectures = 0
        for section in self.enrollment.course.sections.all():
            total_lectures += section.lectures.count()
        
        completed_count = self.completed_lectures.count()
        
        if total_lectures == 0:
            percentage = 0
        else:
            percentage = round((completed_count / total_lectures) * 100, 2)
        
        return {
            'total_lectures': total_lectures,
            'completed_lectures': completed_count,
            'progress_percentage': percentage,
            'remaining_lectures': total_lectures - completed_count
        }

# Signal to update progress when completed_lectures changes
@receiver(m2m_changed, sender=CourseProgress.completed_lectures.through)
def update_enrollment_progress(sender, instance, action, pk_set, **kwargs):
    """
    Update enrollment progress percentage when completed_lectures changes
    """
    if action in ['post_add', 'post_remove', 'post_clear']:
        # Update the enrollment's progress percentage
        instance.enrollment.update_progress_percentage()