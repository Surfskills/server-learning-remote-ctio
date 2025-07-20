# enrollments/models.py
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models.signals import m2m_changed
from django.dispatch import receiver
from django.utils import timezone
from core.models import BaseModel
from authentication.models import User
from users.models import UserActivity

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
    time_spent_minutes = models.PositiveIntegerField(default=0)
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
        """
        Method to add to your Enrollment model
        """
        if self.completed and not getattr(self, '_points_awarded', False):
            try:
                points_info = award_completion_points(self)
                self._points_awarded = True
                return points_info
            except Exception as e:
                print(f"Error awarding completion points: {e}")
                return None

    # Enhanced activity types for better tracking
    ACTIVITY_TYPES = {
        'course_enrolled': 'Course Enrolled',
        'course_completed': 'Course Completed',
        'lecture_completed': 'Lecture Completed',
        'milestone_achieved': 'Milestone Achieved',
        'badge_earned': 'Badge Earned',
        'streak_maintained': 'Learning Streak',
        'quiz_completed': 'Quiz Completed',
        'assignment_submitted': 'Assignment Submitted',
    }

    def log_course_completion_celebration(user, course, completed_courses_count):
        """
        Log the celebratory completion with special messages
        """
        celebration_messages = {
            1: "🎉 First course completed! Welcome to your learning journey!",
            2: "🔥 Two courses down! You're building serious momentum!",
            3: "⚡ Three courses mastered! You're becoming unstoppable!",
            4: "👑 Four courses conquered! You're a true learning champion!",
            5: "🌟 Five courses completed! You're an inspiration to others!",
        }
        
        special_message = celebration_messages.get(
            completed_courses_count, 
            f"🎯 Course #{completed_courses_count} completed! Keep going!"
        )
        
        log_user_activity(
            user=user,
            activity_type='course_completed',
            related_object=course,
            description=special_message
        )
        
        # Log special milestones
        if completed_courses_count in [2, 3, 4, 5]:
            log_user_activity(
                user=user,
                activity_type='milestone_achieved',
                related_object=None,
                description=f"🏆 Milestone unlocked: {completed_courses_count} courses completed!"
            )

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
    def validate_enrollment_lecture_relationship(enrollment, lecture):
        """
        Validate that a lecture belongs to the course associated with the enrollment
        """
        try:
            # Check if lecture belongs to the enrolled course
            if lecture.section.course_id != enrollment.course_id:
                return False, f"Lecture belongs to course {lecture.section.course_id} but enrollment is for course {enrollment.course_id}"
            
            # Check if section exists in the course
            if not enrollment.course.sections.filter(id=lecture.section_id).exists():
                return False, f"Lecture section {lecture.section_id} not found in course {enrollment.course_id}"
            
            # Check if lecture exists in the section
            if not lecture.section.lectures.filter(id=lecture.id).exists():
                return False, f"Lecture {lecture.id} not found in section {lecture.section_id}"
            
            return True, "Validation passed"
            
        except Exception as e:
            return False, f"Validation error: {str(e)}"

    
    def validate_lecture_completion(self, lecture):
        """
        Validate that a lecture can be completed for this progress record
        """
        try:
            # Check enrollment relationship
            if self.enrollment.course_id != lecture.section.course_id:
                return False, f"Lecture belongs to course {lecture.section.course_id} but enrollment is for course {self.enrollment.course_id}"
            
            # Check if lecture is already completed
            if self.completed_lectures.filter(id=lecture.id).exists():
                return False, "Lecture already completed"
            
            # Check if course is published
            if not lecture.section.course.is_published:
                return False, "Course is not published"
            
            return True, "Validation passed"
            
        except Exception as e:
            return False, f"Validation error: {str(e)}"
    
    def mark_lecture_complete(self, lecture):
        """
        Mark a lecture as completed with validation
        """
        # Validate before marking complete
        is_valid, message = self.validate_lecture_completion(lecture)
        if not is_valid:
            return False
        
        # Add lecture to completed lectures
        self.completed_lectures.add(lecture)
        
        # Update last accessed lecture
        self.last_accessed_lecture = lecture
        self.save()
        
        # Check if course is now completed
        if self.is_course_completed() and not self.enrollment.completed:
            self.enrollment.completed = True
            self.enrollment.completed_at = timezone.now()
            self.enrollment.save()
            
            # Award completion points if method exists
            if hasattr(self.enrollment, '_award_completion_points'):
                self.enrollment._award_completion_points()
        
        return True

    def mark_lecture_incomplete(self, lecture):
        """Mark a specific lecture as incomplete"""
        self.completed_lectures.remove(lecture)

    def get_progress_percentage(self):
        """Calculate and return the progress percentage"""
        stats = self.get_progress_stats()
        return stats['progress_percentage']

    def is_course_completed(self):
        """Check if all lectures are completed"""
        stats = self.get_progress_stats()
        return stats['is_completed']
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

def log_user_activity(user, activity_type, related_object=None, points=0, description=None):
    """
    Safely log user activity without causing keyword argument errors
    """
    try:
        # Base activity data
        activity_data = {
            'user': user,
            'activity_type': activity_type,
        }
        
        # Add related object if provided
        if related_object:
            activity_data.update({
                'content_type': ContentType.objects.get_for_model(related_object),
                'object_id': related_object.pk
            })
        
        # Check UserActivity model fields and add accordingly
        user_activity_fields = [field.name for field in UserActivity._meta.fields]
        
        if 'description' in user_activity_fields and description:
            activity_data['description'] = description
        
        if 'points_earned' in user_activity_fields and points:
            activity_data['points_earned'] = points
        elif 'points' in user_activity_fields and points:
            activity_data['points'] = points
        
        # Create the activity
        UserActivity.objects.create(**activity_data)
        
    except Exception as e:
        # Log the error but don't break the main flow
        print(f"Error logging user activity: {e}")

def award_completion_points(enrollment):
    """
    Enhanced completion point awarding with proper activity logging
    """
    user = enrollment.student
    course = enrollment.course
    
    # Base completion points
    base_points = 100
    
    # Bonus points based on course difficulty or duration
    bonus_points = 0
    if hasattr(course, 'difficulty_level'):
        difficulty_bonus = {
            'beginner': 0,
            'intermediate': 50,
            'advanced': 100,
            'expert': 200
        }
        bonus_points += difficulty_bonus.get(course.difficulty_level, 0)
    
    # Duration bonus (1 point per minute of course content)
    if hasattr(course, 'duration') and course.duration:
        bonus_points += min(course.duration, 300)  # Cap at 300 minutes
    
    total_points = base_points + bonus_points
    
    # Award points to user profile
    if hasattr(user, 'extended_profile') and user.extended_profile:
        user.extended_profile.points = (user.extended_profile.points or 0) + total_points
        user.extended_profile.save()
    
    # Log the activity safely
    log_user_activity(
        user=user,
        activity_type='course_completed',
        related_object=course,
        points=total_points,
        description=f"Completed course: {course.title}"
    )
    
    # Check for milestone achievements
    completed_courses_count = Enrollment.objects.filter(
        student=user, 
        completed=True
    ).count()
    
    # Award milestone bonuses
    milestone_rewards = {
        2: 250,
        3: 500, 
        4: 1000,
        5: 2000,
        10: 5000
    }
    
    if completed_courses_count in milestone_rewards:
        milestone_points = milestone_rewards[completed_courses_count]
        
        # Award milestone points
        if hasattr(user, 'extended_profile') and user.extended_profile:
            user.extended_profile.points = (user.extended_profile.points or 0) + milestone_points
            user.extended_profile.save()
        
        # Log milestone achievement
        log_user_activity(
            user=user,
            activity_type='milestone_achieved',
            related_object=None,
            points=milestone_points,
            description=f"Reached milestone: {completed_courses_count} courses completed"
        )
    
    return {
        'base_points': base_points,
        'bonus_points': bonus_points,
        'total_points': total_points,
        'milestone_bonus': milestone_rewards.get(completed_courses_count, 0),
        'completed_courses_count': completed_courses_count
    }
