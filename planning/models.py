# planning/models.py
from django.db import models
from django.core.exceptions import ValidationError
import uuid
from core.models import BaseModel
from authentication.models import User
from courses.models import Course

class CalendarEvent(BaseModel):
    EVENT_TYPE_CHOICES = [
        ('release', 'Content Release'),
        ('meeting', 'Live Meeting'),
        ('assignment', 'Assignment'),
        ('quiz', 'Quiz'),
        ('lecture', 'Lecture'),
    ]
    
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    event_type = models.CharField(max_length=20, choices=EVENT_TYPE_CHOICES)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='calendar_events')
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(blank=True, null=True)
    is_all_day = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    # Fixed: Use string reference to avoid import issues
    related_lecture = models.ForeignKey('courses.Lecture', on_delete=models.SET_NULL, null=True, blank=True, related_name='events')
    attendees = models.ManyToManyField(User, blank=True, related_name='calendar_events')
    location = models.CharField(max_length=200, blank=True, null=True)
    meeting_url = models.URLField(max_length=500, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_events')

    class Meta:
        ordering = ['start_time']

    def __str__(self):
        return f"{self.title} ({self.get_event_type_display()})"

    def clean(self):
        if self.end_time and self.end_time < self.start_time:
            raise ValidationError("End time must be after start time")

class CalendarNotification(BaseModel):
    NOTIFICATION_TYPE_CHOICES = [
        ('reminder', 'Reminder'),
        ('update', 'Update'),
        ('cancellation', 'Cancellation'),
    ]
    
    event = models.ForeignKey(CalendarEvent, on_delete=models.CASCADE, related_name='notifications')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='calendar_notifications')
    type = models.CharField(max_length=20, choices=NOTIFICATION_TYPE_CHOICES)
    message = models.TextField()
    scheduled_for = models.DateTimeField()
    sent = models.BooleanField(default=False)

    class Meta:
        ordering = ['scheduled_for']

    def __str__(self):
        return f"Notification for {self.user.email} about {self.event.title}"

class CalendarPermissions(BaseModel):
    # Fixed: Remove primary_key=True since BaseModel already provides primary key
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='calendar_permissions')
    can_create_events = models.BooleanField(default=False)
    can_edit_events = models.BooleanField(default=False)
    can_delete_events = models.BooleanField(default=False)
    can_view_all_courses = models.BooleanField(default=False)
    allowed_course_ids = models.JSONField(default=list)

    class Meta:
        verbose_name_plural = "Calendar permissions"

    def __str__(self):
        return f"Calendar permissions for {self.user.email}"

class PlannedCourseRelease(BaseModel):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='planned_releases')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='planned_releases')
    release_date = models.DateTimeField()
    section = models.ForeignKey('courses.CourseSection', on_delete=models.SET_NULL, null=True, blank=True, related_name='releases')
    # Fixed: Use string reference to avoid import issues
    lecture = models.ForeignKey('courses.Lecture', on_delete=models.SET_NULL, null=True, blank=True, related_name='releases')
    is_released = models.BooleanField(default=False)
    related_event = models.ForeignKey(CalendarEvent, on_delete=models.SET_NULL, null=True, blank=True, related_name='releases')

    class Meta:
        unique_together = ['course', 'student', 'section', 'lecture']
        ordering = ['release_date']

    def __str__(self):
        return f"Release for {self.student.email} on {self.release_date}"

class StudentProgressControl(BaseModel):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='progress_controls')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='progress_controls')
    # Fixed: Use string reference to avoid import issues
    locked_lectures = models.ManyToManyField('courses.Lecture', blank=True, related_name='locked_for')
    unlocked_lectures = models.ManyToManyField('courses.Lecture', blank=True, related_name='unlocked_for')
    is_auto_release_enabled = models.BooleanField(default=True)

    class Meta:
        unique_together = ['student', 'course']

    def __str__(self):
        return f"Progress control for {self.student.email} in {self.course.title}"

class DripSchedule(BaseModel):
    TYPE_CHOICES = [
        ('fixed', 'Fixed Dates'),
        ('relative', 'Relative to Enrollment'),
    ]
    
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='drip_schedules')
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)

    def __str__(self):
        return f"Drip schedule for {self.course.title}"

class DripScheduleEntry(BaseModel):
    schedule = models.ForeignKey(DripSchedule, on_delete=models.CASCADE, related_name='entries')
    day_offset = models.PositiveIntegerField(blank=True, null=True)  # For relative schedules
    release_date = models.DateTimeField(blank=True, null=True)  # For fixed schedules
    section = models.ForeignKey('courses.CourseSection', on_delete=models.SET_NULL, null=True, blank=True, related_name='drip_entries')
    # Fixed: Use string reference to avoid import issues
    lecture = models.ForeignKey('courses.Lecture', on_delete=models.SET_NULL, null=True, blank=True, related_name='drip_entries')

    class Meta:
        verbose_name_plural = "Drip schedule entries"
        ordering = ['day_offset', 'release_date']

    def clean(self):
        if self.schedule.type == 'fixed' and not self.release_date:
            raise ValidationError("Fixed schedules require a release date")
        if self.schedule.type == 'relative' and not self.day_offset:
            raise ValidationError("Relative schedules require a day offset")

    def __str__(self):
        return f"Entry for {self.schedule}"