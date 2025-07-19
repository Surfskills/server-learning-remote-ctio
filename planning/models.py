from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from core.models import BaseModel
from authentication.models import User
from courses.models import Course, CourseSection, Lecture

class CalendarEvent(BaseModel):
    EVENT_TYPE_CHOICES = [
        ('course', 'Course Related'),
        ('personal', 'Personal'),
        ('meeting', 'Meeting'),
        ('reminder', 'Reminder'),
        ('deadline', 'Deadline'),
    ]
    
    COURSE_EVENT_TYPES = [
        ('release', 'Content Release'),
        ('live_session', 'Live Session'),
        ('quiz', 'Quiz'),
        ('lecture', 'Lecture'),
        ('exam', 'Exam'),
    ]
    
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('postponed', 'Postponed'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    event_type = models.CharField(max_length=20, choices=EVENT_TYPE_CHOICES)
    course_event_type = models.CharField(max_length=20, choices=COURSE_EVENT_TYPES, blank=True, null=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, null=True, blank=True, related_name='calendar_events')
    section = models.ForeignKey(CourseSection, on_delete=models.SET_NULL, null=True, blank=True, related_name='events')
    lecture = models.ForeignKey(Lecture, on_delete=models.SET_NULL, null=True, blank=True, related_name='events')
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(blank=True, null=True)
    is_all_day = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    attendees = models.ManyToManyField(User, blank=True, related_name='calendar_events')
    location = models.CharField(max_length=200, blank=True, null=True)
    meeting_url = models.URLField(max_length=500, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_events')
    is_recurring = models.BooleanField(default=False)
    recurrence_pattern = models.CharField(max_length=100, blank=True, null=True)
    color = models.CharField(max_length=20, default='#3b82f6')  # Default blue color

    class Meta:
        ordering = ['start_time']
        indexes = [
            models.Index(fields=['start_time', 'end_time']),
            models.Index(fields=['course', 'section', 'lecture']),
        ]

    def __str__(self):
        return f"{self.title} ({self.get_event_type_display()})"

    def clean(self):
        if self.end_time and self.end_time < self.start_time:
            raise ValidationError("End time must be after start time")
        
        # Validate course-related events
        if self.event_type == 'course' and not self.course:
            raise ValidationError("Course must be specified for course-related events")
        
        if self.course_event_type and not self.course:
            raise ValidationError("Course must be specified when course event type is set")

    @property
    def is_course_event(self):
        return self.event_type == 'course'

    def get_related_course_content(self):
        if not self.is_course_event:
            return None
        
        return {
            'course': self.course,
            'section': self.section,
            'lecture': self.lecture
        }

class CalendarNotification(BaseModel):
    NOTIFICATION_TYPE_CHOICES = [
        ('reminder', 'Reminder'),
        ('update', 'Update'),
        ('cancellation', 'Cancellation'),
        ('new_event', 'New Event'),
    ]
    
    DELIVERY_METHOD_CHOICES = [
        ('email', 'Email'),
        ('push', 'Push Notification'),
        ('both', 'Email and Push'),
    ]
    
    event = models.ForeignKey(CalendarEvent, on_delete=models.CASCADE, related_name='notifications')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='calendar_notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPE_CHOICES)
    delivery_method = models.CharField(max_length=10, choices=DELIVERY_METHOD_CHOICES, default='both')
    message = models.TextField()
    scheduled_for = models.DateTimeField()
    sent = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['scheduled_for']
        indexes = [
            models.Index(fields=['event', 'user']),
            models.Index(fields=['scheduled_for', 'sent']),
        ]

    def __str__(self):
        return f"Notification for {self.user.email} about {self.event.title}"

    def send(self):
        # Placeholder for actual notification sending logic
        self.sent = True
        self.sent_at = timezone.now()
        self.save()

class UserCalendarSettings(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='calendar_settings')
    default_view = models.CharField(max_length=20, default='week', choices=[
        ('day', 'Day'),
        ('week', 'Week'),
        ('month', 'Month'),
        ('agenda', 'Agenda'),
    ])
    time_zone = models.CharField(max_length=50, default='UTC')
    working_hours_start = models.TimeField(default='09:00:00')
    working_hours_end = models.TimeField(default='17:00:00')
    default_event_duration = models.PositiveIntegerField(default=60)  # in minutes
    enable_email_notifications = models.BooleanField(default=True)
    enable_push_notifications = models.BooleanField(default=True)
    reminder_minutes_before = models.JSONField(default=list)  # e.g. [5, 15, 30, 60]
    color_scheme = models.CharField(max_length=20, default='default')
    show_week_numbers = models.BooleanField(default=False)
    first_day_of_week = models.PositiveIntegerField(default=0, choices=[(i, f'Day {i}') for i in range(7)])

    def __str__(self):
        return f"Calendar settings for {self.user.email}"


class ContentReleaseSchedule(BaseModel):
    RELEASE_STRATEGY_CHOICES = [
        ('fixed_dates', 'Fixed Dates'),
        ('relative_enrollment', 'Relative to Enrollment'),
        ('self_paced', 'Self-Paced'),
        ('drip', 'Drip Content'),
    ]
    
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='release_schedules')
    strategy = models.CharField(max_length=20, choices=RELEASE_STRATEGY_CHOICES)
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    unlock_all = models.BooleanField(default=False)
    days_between_releases = models.PositiveIntegerField(null=True, blank=True)
    release_time = models.TimeField(default='00:00:00')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_schedules')

    def __str__(self):
        return f"Release schedule for {self.course.title}"
    
    def get_content_availability(self, user, content_object):
        """
        Check if content is available for a specific user based on release rules
        """
        from courses.models import Lecture, CourseSection
        
        # If unlock_all is True, everything is available
        if self.unlock_all:
            return True
            
        # If self-paced strategy, everything is available
        if self.strategy == 'self_paced':
            return True
        
        # Determine what type of content we're dealing with
        if isinstance(content_object, Lecture):
            # For lectures, check both lecture-specific rules and section-level rules
            rule = self.rules.filter(
                models.Q(lecture=content_object) |  # Direct lecture rule
                models.Q(section=content_object.section, lecture__isnull=True)  # Section rule without specific lecture
            ).first()
            
        elif isinstance(content_object, CourseSection):
            # For sections, only check section-level rules
            rule = self.rules.filter(
                models.Q(section=content_object)
            ).first()
            
        else:
            # For other content types (like quizzes), handle appropriately
            rule = self.rules.filter(
                models.Q(quiz=content_object)
            ).first()
        
        # If no rule found, content is available by default
        if not rule:
            return True
        
        # Check if the rule allows access
        return rule.is_content_available(user)


class ContentReleaseRule(BaseModel):
    TRIGGER_CHOICES = [
        ('enrollment', 'Upon Enrollment'),
        ('date', 'Specific Date'),
        ('completion', 'After Previous Completion'),
        ('progress', 'Progress-based'),
        ('manual', 'Manual Release'),
        ('quiz_completion', 'Quiz Completion'),  # New trigger type
        ('quiz_performance', 'Quiz Performance'),  # New trigger type
    ]
    
    schedule = models.ForeignKey(ContentReleaseSchedule, on_delete=models.CASCADE, related_name='rules')
    trigger = models.CharField(max_length=20, choices=TRIGGER_CHOICES)
    offset_days = models.PositiveIntegerField(default=0)
    release_date = models.DateTimeField(null=True, blank=True)
    section = models.ForeignKey(CourseSection, on_delete=models.CASCADE, null=True, blank=True)
    lecture = models.ForeignKey(Lecture, on_delete=models.CASCADE, null=True, blank=True)
    quiz = models.ForeignKey('courses.Quiz', on_delete=models.CASCADE, null=True, blank=True)
    is_released = models.BooleanField(default=False)
    is_manually_unlocked = models.BooleanField(default=False)
    required_progress_percentage = models.PositiveIntegerField(null=True, blank=True)
    required_completion_item = models.CharField(max_length=200, null=True, blank=True)
    required_quiz_score = models.PositiveIntegerField(null=True, blank=True, 
        help_text="Minimum score percentage required for quiz performance trigger")
    release_event = models.ForeignKey(CalendarEvent, on_delete=models.SET_NULL, null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_release_rules')

    class Meta:
        ordering = ['release_date', 'offset_days']
        unique_together = ['schedule', 'section', 'lecture', 'quiz']

    def clean(self):
        if self.trigger == 'date' and not self.release_date:
            raise ValidationError("Release date is required for date-triggered rules")
        
        if self.trigger == 'enrollment' and not self.offset_days:
            raise ValidationError("Offset days is required for enrollment-triggered rules")
        
        if self.trigger == 'progress' and not self.required_progress_percentage:
            raise ValidationError("Required progress percentage is required for progress-triggered rules")
            
        if self.trigger == 'quiz_completion' and not self.quiz:
            raise ValidationError("Quiz must be specified for quiz completion trigger")
            
        if self.trigger == 'quiz_performance' and not self.quiz:
            raise ValidationError("Quiz must be specified for quiz performance trigger")
            
        if self.trigger == 'quiz_performance' and not self.required_quiz_score:
            raise ValidationError("Required quiz score is required for quiz performance trigger")
        
    def __str__(self):
        return f"Release rule for {self.schedule.course.title}"
    
    def is_available_for_user(self, user):
        """
        Legacy method - kept for backward compatibility
        """
        return self.is_content_available(user)
    
    def is_content_available(self, user):
        """
        Check if content is available for a specific user based on this rule
        """
        from django.utils import timezone
        
        # Check for student-specific overrides first
        override = self.student_overrides.filter(student=user).first()
        if override:
            return override.is_released
        
        # Check rule type and conditions
        if self.trigger == 'date':
            # Date-based release
            if self.release_date:
                return timezone.now() >= self.release_date
            return False
            
        elif self.trigger == 'progress':
            # Progress-based release
            if self.required_progress_percentage:
                try:
                    from enrollments.models import CourseProgress
                    progress = CourseProgress.objects.get(
                        enrollment__student=user,
                        enrollment__course=self.schedule.course
                    )
                    return progress.overall_progress >= self.required_progress_percentage
                except (ImportError, CourseProgress.DoesNotExist):
                    return False
            return False
            
        elif self.trigger == 'completion':
            # Completion-based release
            if self.required_completion_item:
                # Check if user has completed the required item
                # Implementation depends on your completion tracking system
                return False
            return False
            
        elif self.trigger == 'enrollment':
            # Enrollment-based release with offset
            try:
                enrollment = user.enrollments.filter(course=self.schedule.course).first()
                if not enrollment:
                    return False
                release_date = enrollment.enrolled_at + timedelta(days=self.offset_days)
                return timezone.now() >= release_date
            except AttributeError:
                return False
            
        elif self.trigger == 'manual':
            # Manual release - check if manually unlocked
            return self.is_manually_unlocked
            
        elif self.trigger == 'quiz_completion':
            # Quiz completion trigger
            if not self.quiz:
                return False
                
            try:
                from courses.models import QuizAttempt
                # Check if user has completed the quiz
                return QuizAttempt.objects.filter(
                    quiz=self.quiz,
                    user=user,
                    is_completed=True
                ).exists()
            except (ImportError, QuizAttempt.DoesNotExist):
                return False
                
        elif self.trigger == 'quiz_performance':
            # Quiz performance trigger
            if not self.quiz or not self.required_quiz_score:
                return False
                
            try:
                from courses.models import QuizAttempt
                # Check if user has achieved the required score
                best_attempt = QuizAttempt.objects.filter(
                    quiz=self.quiz,
                    user=user,
                    is_completed=True
                ).order_by('-score').first()
                
                if best_attempt:
                    score_percentage = (best_attempt.score / best_attempt.quiz.total_points) * 100
                    return score_percentage >= self.required_quiz_score
                return False
            except (ImportError, QuizAttempt.DoesNotExist):
                return False
            
        # Default to not available if no conditions match
        return False


    @property
    def prerequisite_lecture(self):
        return self.lecture or None

    @property
    def prerequisite_section(self):
        if self.section:
            return self.section
        if self.lecture:
            return self.lecture.section
        return None


class StudentProgressOverride(BaseModel):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='progress_overrides')
    rule = models.ForeignKey(ContentReleaseRule, on_delete=models.CASCADE, related_name='student_overrides')
    override_date = models.DateTimeField(null=True, blank=True)
    is_released = models.BooleanField(default=False)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ['student', 'rule']

    def __str__(self):
        return f"Override for {self.student.email} on {self.rule}"