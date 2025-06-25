from django.db import models

from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.models import JSONField
import uuid
from authentication.models import User

class CourseCategory(models.Model):
    LEVEL_CHOICES = [
        ('Beginner', 'Beginner'),
        ('Intermediate', 'Intermediate'),
        ('Advanced', 'Advanced'),
        ('All Levels', 'All Levels'),
    ]
    
    # Add default=uuid.uuid4 to automatically generate UUIDs
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Course Categories"
        ordering = ['name']

    def __str__(self):
        return self.name
    

class Course(models.Model):
    LANGUAGE_CHOICES = [
        ('en', 'English'),
        ('es', 'Spanish'),
        ('fr', 'French'),
        ('de', 'German'),
        ('pt', 'Portuguese'),
        ('ru', 'Russian'),
        ('zh', 'Chinese'),
        ('ja', 'Japanese'),
        ('ar', 'Arabic'),
    ]
    
    # FIXED: Added default=uuid.uuid4
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField()
    long_description = models.TextField(blank=True, null=True)
    banner_url = models.URLField(max_length=500)
    preview_video_url = models.URLField(max_length=500, blank=True, null=True)
    instructor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='courses_taught')
    category = models.ForeignKey(CourseCategory, on_delete=models.SET_NULL, null=True, related_name='courses')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    level = models.CharField(max_length=20, choices=CourseCategory.LEVEL_CHOICES)
    language = models.CharField(max_length=10, choices=LANGUAGE_CHOICES, default='en')
    duration = models.CharField(max_length=20)  # e.g. "5h 30m"
    rating = models.FloatField(default=0, validators=[MinValueValidator(0), MaxValueValidator(5)])
    review_count = models.PositiveIntegerField(default=0)
    students_enrolled = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if self.is_published and not self.published_at:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)

    @property
    def current_price(self):
        return self.discount_price if self.discount_price else self.price

class CourseSection(models.Model):
    # FIXED: Added default=uuid.uuid4
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='sections')
    title = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order']
        unique_together = ['course', 'order']

    def __str__(self):
        return f"{self.course.title} - {self.title}"

class Lecture(models.Model):
    # FIXED: Added default=uuid.uuid4
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    section = models.ForeignKey(CourseSection, on_delete=models.CASCADE, related_name='lectures')
    title = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=0)
    duration = models.CharField(max_length=20)  # e.g. "30m"
    overview = models.TextField(blank=True, null=True)
    preview_available = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order']
        unique_together = ['section', 'order']

    def __str__(self):
        return f"{self.section.course.title} - {self.section.title} - {self.title}"

class LectureResource(models.Model):
    RESOURCE_KIND_CHOICES = [
        ('video', 'Video'),
        ('pdf', 'PDF'),
        ('link', 'Link'),
        ('file', 'File'),
    ]
    
    PROVIDER_CHOICES = [
        ('youtube', 'YouTube'),
        ('vimeo', 'Vimeo'),
        ('self', 'Self-hosted'),
        ('drive', 'Google Drive'),
        ('dropbox', 'Dropbox'),
        ('external', 'External'),
    ]
    
    # FIXED: Added default=uuid.uuid4
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lecture = models.ForeignKey(Lecture, on_delete=models.CASCADE, related_name='resources')
    title = models.CharField(max_length=200)
    kind = models.CharField(max_length=10, choices=RESOURCE_KIND_CHOICES)
    url = models.URLField(max_length=500)
    provider = models.CharField(max_length=10, choices=PROVIDER_CHOICES, blank=True, null=True)
    duration_seconds = models.PositiveIntegerField(blank=True, null=True)
    is_downloadable = models.BooleanField(default=False)
    file_size = models.PositiveIntegerField(blank=True, null=True)  # in bytes
    mime_type = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.lecture.title} - {self.title}"

class QaItem(models.Model):
    # FIXED: Added default=uuid.uuid4
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lecture = models.ForeignKey(Lecture, on_delete=models.CASCADE, related_name='qa_items')
    question = models.TextField()
    answer = models.TextField(blank=True, null=True)
    asked_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='questions_asked')
    date = models.DateTimeField(auto_now_add=True)
    upvotes = models.PositiveIntegerField(default=0)
    resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"Q: {self.question[:50]}..."

class ProjectTool(models.Model):
    # FIXED: Added default=uuid.uuid4
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lecture = models.ForeignKey(Lecture, on_delete=models.CASCADE, related_name='project_tools')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    url = models.URLField(max_length=500)
    icon = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class Enrollment(models.Model):
    # FIXED: Added default=uuid.uuid4
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='enrollments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')
    enrolled_at = models.DateTimeField(auto_now_add=True)
    completed = models.BooleanField(default=False)
    progress_percentage = models.FloatField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    last_accessed = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['student', 'course']
        ordering = ['-enrolled_at']

    def __str__(self):
        return f"{self.student.email} enrolled in {self.course.title}"

class CourseProgress(models.Model):
    enrollment = models.OneToOneField(Enrollment, on_delete=models.CASCADE, primary_key=True, related_name='progress')
    completed_lectures = models.ManyToManyField(Lecture, blank=True)
    last_accessed_lecture = models.ForeignKey(Lecture, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def progress_percentage(self):
        total_lectures = self.enrollment.course.lectures.count()
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

class Review(models.Model):
    # FIXED: Added default=uuid.uuid4
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='reviews')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['course', 'student']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.rating} stars by {self.student.email} for {self.course.title}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.update_course_rating()

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        self.update_course_rating()

    def update_course_rating(self):
        course = self.course
        reviews = course.reviews.all()
        count = reviews.count()
        if count > 0:
            total = sum(review.rating for review in reviews)
            course.rating = total / count
            course.review_count = count
            course.save()

class Quiz(models.Model):
    # FIXED: Added default=uuid.uuid4
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='quizzes')
    section = models.ForeignKey(CourseSection, on_delete=models.SET_NULL, null=True, blank=True, related_name='quizzes')
    lecture = models.ForeignKey(Lecture, on_delete=models.SET_NULL, null=True, blank=True, related_name='quizzes')
    title = models.CharField(max_length=200)
    description = models.TextField()
    instructions = models.TextField()
    due_date = models.DateTimeField(blank=True, null=True)
    points_possible = models.PositiveIntegerField(default=10)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Quizzes"
        ordering = ['due_date']

    def __str__(self):
        return f"{self.course.title} - {self.title}"

class QuizQuestion(models.Model):
    # FIXED: Added default=uuid.uuid4
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    question = models.TextField()
    options = JSONField()  # List of strings
    correct_option_index = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']

    def clean(self):
        if not isinstance(self.options, list):
            raise ValidationError("Options must be a list of strings")
        if self.correct_option_index >= len(self.options):
            raise ValidationError("Correct option index is out of range")

    def __str__(self):
        return f"Question for {self.quiz.title}"

class QuizTask(models.Model):
    SUBMISSION_FILE_TYPE_CHOICES = [
        ('video', 'Video'),
        ('pdf', 'PDF'),
        ('image', 'Image'),
        ('audio', 'Audio'),
        ('document', 'Document'),
        ('code', 'Code'),
    ]
    
    # FIXED: Added default=uuid.uuid4
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if self.accepted_file_types and not isinstance(self.accepted_file_types, list):
            raise ValidationError("Accepted file types must be a list")
        if self.accepted_file_types:
            for file_type in self.accepted_file_types:
                if file_type not in dict(self.SUBMISSION_FILE_TYPE_CHOICES).keys():
                    raise ValidationError(f"Invalid file type: {file_type}")

    def __str__(self):
        return f"Task for {self.quiz.title}"

class GradingCriterion(models.Model):
    # FIXED: Added default=uuid.uuid4
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(QuizTask, on_delete=models.CASCADE, related_name='grading_criteria')
    description = models.TextField()
    points = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Grading Criteria"

    def __str__(self):
        return f"Criterion for {self.task}"

class QuizSubmission(models.Model):
    STATUS_CHOICES = [
        ('submitted', 'Submitted'),
        ('graded', 'Graded'),
        ('needs_revision', 'Needs Revision'),
    ]
    
    # FIXED: Added default=uuid.uuid4
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quiz_submissions')
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='submissions')
    submitted_at = models.DateTimeField(auto_now_add=True)
    text_response = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='submitted')
    grade = models.FloatField(blank=True, null=True)
    feedback = models.TextField(blank=True, null=True)
    instructor_notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['student', 'quiz']
        ordering = ['-submitted_at']

    def __str__(self):
        return f"{self.student.email}'s submission for {self.quiz.title}"

class SubmissionFile(models.Model):
    # FIXED: Added default=uuid.uuid4
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    submission = models.ForeignKey(QuizSubmission, on_delete=models.CASCADE, related_name='files')
    url = models.URLField(max_length=500)
    type = models.CharField(max_length=10, choices=QuizTask.SUBMISSION_FILE_TYPE_CHOICES)
    name = models.CharField(max_length=200)
    size = models.PositiveIntegerField()  # in bytes
    mime_type = models.CharField(max_length=100)
    thumbnail_url = models.URLField(max_length=500, blank=True, null=True)
    duration = models.PositiveIntegerField(blank=True, null=True)  # in seconds
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"File for {self.submission}"

class QuizGrade(models.Model):
    # FIXED: Added default=uuid.uuid4
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='grades')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quiz_grades')
    overall_score = models.FloatField()
    feedback = models.TextField(blank=True, null=True)
    graded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='graded_quizzes')
    graded_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['quiz', 'student']
        ordering = ['-graded_at']

    def __str__(self):
        return f"Grade for {self.student.email} on {self.quiz.title}"

class TaskGrade(models.Model):
    # FIXED: Added default=uuid.uuid4
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    grade = models.ForeignKey(QuizGrade, on_delete=models.CASCADE, related_name='task_grades')
    task = models.ForeignKey(QuizTask, on_delete=models.CASCADE, related_name='grades')
    score = models.FloatField()
    feedback = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Task grade for {self.grade}"

class CriteriaGrade(models.Model):
    # FIXED: Added default=uuid.uuid4
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task_grade = models.ForeignKey(TaskGrade, on_delete=models.CASCADE, related_name='criteria_grades')
    criterion = models.ForeignKey(GradingCriterion, on_delete=models.CASCADE, related_name='grades')
    awarded_points = models.PositiveIntegerField()
    comments = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Criteria grade for {self.task_grade}"

class Order(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('card', 'Credit Card'),
        ('paypal', 'PayPal'),
        ('mpesa', 'M-Pesa'),
        ('crypto', 'Cryptocurrency'),
    ]
    
    STATUS_CHOICES = [
        ('paid', 'Paid'),
        ('pending', 'Pending'),
        ('failed', 'Failed'),
    ]
    
    # FIXED: Added default=uuid.uuid4
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='orders')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHOD_CHOICES)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    purchased_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-purchased_at']

    def __str__(self):
        return f"Order #{self.id} for {self.user.email}"

class Certificate(models.Model):
    # FIXED: Added default=uuid.uuid4
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='certificates')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='certificates')
    issued_at = models.DateTimeField(auto_now_add=True)
    certificate_url = models.URLField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['student', 'course']
        ordering = ['-issued_at']

    def __str__(self):
        return f"Certificate for {self.student.email} on {self.course.title}"

class Faq(models.Model):
    # FIXED: Added default=uuid.uuid4
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='faqs')
    question = models.CharField(max_length=200)
    answer = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "FAQ"
        verbose_name_plural = "FAQs"
        ordering = ['created_at']

    def __str__(self):
        return f"FAQ for {self.course.title}"

class Announcement(models.Model):
    # FIXED: Added default=uuid.uuid4
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='announcements')
    title = models.CharField(max_length=200)
    content = models.TextField()
    published_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-published_at']

    def __str__(self):
        return f"Announcement for {self.course.title}"

class CalendarEvent(models.Model):
    EVENT_TYPE_CHOICES = [
        ('release', 'Content Release'),
        ('meeting', 'Live Meeting'),
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
    
    # FIXED: Added default=uuid.uuid4
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    event_type = models.CharField(max_length=20, choices=EVENT_TYPE_CHOICES)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='calendar_events')
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(blank=True, null=True)
    is_all_day = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    related_lecture = models.ForeignKey(Lecture, on_delete=models.SET_NULL, null=True, blank=True, related_name='events')
    attendees = models.ManyToManyField(User, blank=True, related_name='calendar_events')
    location = models.CharField(max_length=200, blank=True, null=True)
    meeting_url = models.URLField(max_length=500, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_events')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['start_time']

    def __str__(self):
        return f"{self.title} ({self.get_event_type_display()})"

    def clean(self):
        if self.end_time and self.end_time < self.start_time:
            raise ValidationError("End time must be after start time")

class CalendarNotification(models.Model):
    NOTIFICATION_TYPE_CHOICES = [
        ('reminder', 'Reminder'),
        ('update', 'Update'),
        ('cancellation', 'Cancellation'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(CalendarEvent, on_delete=models.CASCADE, related_name='notifications')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='calendar_notifications')
    type = models.CharField(max_length=20, choices=NOTIFICATION_TYPE_CHOICES)
    message = models.TextField()
    scheduled_for = models.DateTimeField()
    sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['scheduled_for']

    def __str__(self):
        return f"Notification for {self.user.email} about {self.event.title}"

class NotificationPreferences(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True, related_name='notification_preferences')
    email_notifications = models.BooleanField(default=True)
    push_notifications = models.BooleanField(default=True)
    reminder_minutes = JSONField(default=list)  # e.g., [15, 60, 1440] for 15min, 1hr, 1day
    event_types = JSONField(default=list)  # List of CalendarEvent.EVENT_TYPE_CHOICES
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Notification preferences for {self.user.email}"

class CalendarPermissions(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True, related_name='calendar_permissions')
    can_create_events = models.BooleanField(default=False)
    can_edit_events = models.BooleanField(default=False)
    can_delete_events = models.BooleanField(default=False)
    can_view_all_courses = models.BooleanField(default=False)
    allowed_course_ids = JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Calendar permissions"

    def __str__(self):
        return f"Calendar permissions for {self.user.email}"

class PlannedCourseRelease(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='planned_releases')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='planned_releases')
    release_date = models.DateTimeField()
    section = models.ForeignKey(CourseSection, on_delete=models.SET_NULL, null=True, blank=True, related_name='releases')
    lecture = models.ForeignKey(Lecture, on_delete=models.SET_NULL, null=True, blank=True, related_name='releases')
    is_released = models.BooleanField(default=False)
    related_event = models.ForeignKey(CalendarEvent, on_delete=models.SET_NULL, null=True, blank=True, related_name='releases')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['course', 'student', 'section', 'lecture']
        ordering = ['release_date']

    def __str__(self):
        return f"Release for {self.student.email} on {self.release_date}"

class StudentProgressControl(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='progress_controls')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='progress_controls')
    locked_lectures = models.ManyToManyField(Lecture, blank=True, related_name='locked_for')
    unlocked_lectures = models.ManyToManyField(Lecture, blank=True, related_name='unlocked_for')
    is_auto_release_enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['student', 'course']

    def __str__(self):
        return f"Progress control for {self.student.email} in {self.course.title}"

class DripSchedule(models.Model):
    TYPE_CHOICES = [
        ('fixed', 'Fixed Dates'),
        ('relative', 'Relative to Enrollment'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='drip_schedules')
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Drip schedule for {self.course.title}"

class DripScheduleEntry(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    schedule = models.ForeignKey(DripSchedule, on_delete=models.CASCADE, related_name='entries')
    day_offset = models.PositiveIntegerField(blank=True, null=True)  # For relative schedules
    release_date = models.DateTimeField(blank=True, null=True)  # For fixed schedules
    section = models.ForeignKey(CourseSection, on_delete=models.SET_NULL, null=True, blank=True, related_name='drip_entries')
    lecture = models.ForeignKey(Lecture, on_delete=models.SET_NULL, null=True, blank=True, related_name='drip_entries')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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