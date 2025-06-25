from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
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
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_schedules')  # Add this field

    def __str__(self):
        return f"Release schedule for {self.course.title}"

class ContentReleaseRule(BaseModel):
    schedule = models.ForeignKey(ContentReleaseSchedule, on_delete=models.CASCADE, related_name='rules')
    trigger = models.CharField(max_length=20, choices=[
        ('enrollment', 'Upon Enrollment'),
        ('date', 'Specific Date'),
        ('completion', 'After Previous Completion'),
        ('manual', 'Manual Release'),
    ])
    offset_days = models.PositiveIntegerField(default=0)
    release_date = models.DateTimeField(null=True, blank=True)
    section = models.ForeignKey(CourseSection, on_delete=models.CASCADE, null=True, blank=True)
    lecture = models.ForeignKey(Lecture, on_delete=models.CASCADE, null=True, blank=True)
    quiz = models.ForeignKey('courses.Quiz', on_delete=models.CASCADE, null=True, blank=True)
    is_released = models.BooleanField(default=False)
    release_event = models.ForeignKey(CalendarEvent, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ['release_date', 'offset_days']
        unique_together = ['schedule', 'section', 'lecture', 'quiz']

    def clean(self):
        if self.trigger == 'date' and not self.release_date:
            raise ValidationError("Release date is required for date-triggered rules")
        
        if self.trigger == 'enrollment' and not self.offset_days:
            raise ValidationError("Offset days is required for enrollment-triggered rules")

    def __str__(self):
        return f"Release rule for {self.schedule.course.title}"

class StudentProgressOverride(BaseModel):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='progress_overrides')
    rule = models.ForeignKey(ContentReleaseRule, on_delete=models.CASCADE)
    override_date = models.DateTimeField(null=True, blank=True)
    is_released = models.BooleanField(default=False)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ['student', 'rule']

    def __str__(self):
        return f"Override for {self.student.email} on {self.rule}"