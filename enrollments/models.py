# enrollments/models.py
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models.signals import m2m_changed
from django.dispatch import receiver
from django.utils import timezone
from core.models import BaseModel
from authentication.models import User

class Enrollment(BaseModel):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='enrollments')
    course = models.ForeignKey('courses.Course', on_delete=models.CASCADE, related_name='enrollments')
    enrolled_at = models.DateTimeField(auto_now_add=True)
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)  # Track when course was completed
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
        """Update progress percentage based on completed lectures and check for course completion"""
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
                
                # Check if all lectures are completed and auto-complete the course
                if completed_count == total_lectures and total_lectures > 0:
                    if not self.completed:  # Only update if not already completed
                        self.completed = True
                        self.completed_at = timezone.now()
                        # You could add points/achievements here
                        self._award_completion_points()
                elif self.completed and completed_count < total_lectures:
                    # If course was completed but lectures were uncompleted, revert completion
                    self.completed = False
                    self.completed_at = None
            
            self.save(update_fields=['progress_percentage', 'completed', 'completed_at'])
        except CourseProgress.DoesNotExist:
            self.progress_percentage = 0
            self.save(update_fields=['progress_percentage'])

    def _award_completion_points(self):
        """Award points to user for course completion"""
        try:
            # Award points based on course difficulty or a fixed amount
            points_to_award = getattr(self.course, 'completion_points', 100)  # Default 100 points
            
            if hasattr(self.student, 'extended_profile'):
                current_points = self.student.extended_profile.points or 0
                self.student.extended_profile.points = current_points + points_to_award
                self.student.extended_profile.save(update_fields=['points'])
                
                # Create user activity for course completion
                from users.models import UserActivity
                UserActivity.objects.create(
                    user=self.student,
                    activity_type='course_completed',
                    description=f'Completed course: {self.course.title}',
                    points_earned=points_to_award
                )
        except Exception as e:
            # Log the error but don't fail the enrollment update
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error awarding completion points: {e}")

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
            'remaining_lectures': total_lectures - completed_count,
            'is_completed': completed_count == total_lectures and total_lectures > 0
        }
    def mark_lecture_complete(self, lecture):
        """Mark a specific lecture as complete with validation"""
        # Validate lecture belongs to the course
        if lecture.section.course != self.enrollment.course:
            raise ValueError(
                f"Lecture does not belong to this course. "
                f"Lecture course: {lecture.section.course.id}, "
                f"Enrollment course: {self.enrollment.course.id}"
            )
        
        # Rest of the method remains the same
        self.completed_lectures.add(lecture)
        self.last_accessed_lecture = lecture
        self.save(update_fields=['last_accessed_lecture'])

    def mark_lecture_incomplete(self, lecture):
        """Mark a specific lecture as incomplete"""
        self.completed_lectures.remove(lecture)

# Signal to update progress when completed_lectures changes
@receiver(m2m_changed, sender=CourseProgress.completed_lectures.through)
def update_enrollment_progress(sender, instance, action, pk_set, **kwargs):
    """
    Update enrollment progress percentage when completed_lectures changes
    Also handles automatic course completion
    """
    if action in ['post_add', 'post_remove', 'post_clear']:
        # Update the enrollment's progress percentage and check for completion
        instance.enrollment.update_progress_percentage()
        
        # Optional: Send notification if course was just completed
        if action == 'post_add' and instance.enrollment.completed:
            try:
                # You can add notification logic here
                # send_course_completion_notification(instance.enrollment)
                pass
            except Exception:
                pass