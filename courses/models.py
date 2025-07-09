# models.py
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.utils.text import slugify
from django.utils.crypto import get_random_string
from django.db.models import Q
from core.models import BaseModel
from authentication.models import User
# REMOVED: from enrollments.models import Enrollment

class CourseCategory(BaseModel):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True) 

    class Meta:
        verbose_name_plural = "Course Categories"
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

class Course(BaseModel):
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
    
    LEVEL_CHOICES = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    ]
    
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField()
    long_description = models.TextField(blank=True, null=True)
    banner_url = models.URLField(max_length=500, blank=True, null=True)
    thumbnail = models.URLField(blank=True, null=True)
    preview_video_url = models.URLField(max_length=500, blank=True, null=True)
    instructor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='courses_taught')
    category = models.ForeignKey('CourseCategory', on_delete=models.SET_NULL, null=True, blank=True, related_name='courses')
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default='beginner')
    language = models.CharField(max_length=10, choices=LANGUAGE_CHOICES, default='en')
    duration = models.CharField(max_length=20, blank=True, null=True)
    rating = models.FloatField(default=0, validators=[MinValueValidator(0), MaxValueValidator(5)])
    review_count = models.PositiveIntegerField(default=0)
    students_enrolled = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    published_at = models.DateTimeField(blank=True, null=True)
    prerequisites = models.ManyToManyField(
        'self',
        blank=True,
        symmetrical=False,
        related_name='prerequisite_for',
        help_text="Courses that must be completed before this course"
    )
    what_you_will_learn = models.TextField(blank=True, null=True)
    who_is_this_for = models.TextField(blank=True, null=True)
    certificate_available = models.BooleanField(default=False)
    lifetime_access = models.BooleanField(default=True) 

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title
    
    def is_content_available_for(self, user, content_object):
        """
        Check if content is available for a specific user based on release rules
        """
        if not hasattr(self, 'release_schedule'):
            return True  # No schedule means all content is available
        
        if self.release_schedule.unlock_all:
            return True
            
        try:
            # Use string reference to avoid circular import
            from django.apps import apps
            Enrollment = apps.get_model('enrollments', 'Enrollment')
            enrollment = self.enrollments.get(student=user)
        except Exception:  # Catch both DoesNotExist and import issues
            return False
            
        # Check release rules
        rules = self.release_schedule.rules.filter(
            Q(section=content_object) |
            Q(lecture=content_object) |
            Q(quiz=content_object) |
            Q(assignment=content_object)
        )
        
        if not rules.exists():
            return True  # No specific rules for this content
            
        for rule in rules:
            if rule.trigger == 'enrollment':
                days_since_enrollment = (timezone.now() - enrollment.enrolled_at).days
                if days_since_enrollment >= rule.offset_days:
                    return True
            elif rule.trigger == 'date' and rule.release_date:
                if timezone.now() >= rule.release_date:
                    return True
            elif rule.trigger == 'completion':
                # Check if prerequisite content is completed
                pass
                
        return False
    
    def generate_unique_slug(self):
        """Generate a unique slug for the course"""
        base_slug = slugify(self.title)
        if not base_slug:  # Handle edge case where title has no alphanumeric characters
            base_slug = f"course-{get_random_string(8).lower()}"
        
        slug = base_slug
        counter = 1
        
        # Keep trying until we find a unique slug
        # Exclude current instance if updating
        queryset = Course.objects.filter(slug=slug)
        if self.pk:
            queryset = queryset.exclude(pk=self.pk)
            
        while queryset.exists():
            slug = f"{base_slug}-{counter}"
            queryset = Course.objects.filter(slug=slug)
            if self.pk:
                queryset = queryset.exclude(pk=self.pk)
            counter += 1
            
        return slug
        
    def save(self, *args, **kwargs):
        # Only check for title changes if this is an existing course (has pk and exists in DB)
        title_changed = False
        if self.pk:
            try:
                old_course = Course.objects.get(pk=self.pk)
                title_changed = old_course.title != self.title
            except Course.DoesNotExist:
                # This handles the edge case where pk exists but object doesn't exist in DB
                title_changed = True
        
        # Generate or update slug if it's a new course, title has changed, or slug is empty
        if not self.slug or title_changed or not self.pk:
            self.slug = self.generate_unique_slug()
        
        # Handle publication timestamp
        if self.is_published and not self.published_at:
            self.published_at = timezone.now()
            
        super().save(*args, **kwargs)


    @property
    def current_price(self):
        return self.discount_price if self.discount_price else self.price

    @property
    def thumbnail_url(self):
        if self.thumbnail:
            return self.thumbnail.url
        return self.banner_url
    
    def total_lectures_count(self):
        """Count all lectures in all sections of this course"""
        return sum(section.lectures.count() for section in self.sections.all())

class CourseSection(BaseModel):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='sections')
    title = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=0)
    description = models.TextField(blank=True, null=True)
    class Meta:
        ordering = ['order']
        unique_together = ['course', 'order']

    def __str__(self):
        return f"{self.course.title} - {self.title}"

class Lecture(BaseModel):
    section = models.ForeignKey(CourseSection, on_delete=models.CASCADE, related_name='lectures')
    title = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=0)
    duration = models.CharField(max_length=20, blank=True, null=True)
    overview = models.TextField(blank=True, null=True)
    video_url = models.URLField(max_length=500, blank=True, null=True)
    preview_available = models.BooleanField(default=False)

    class Meta:
        ordering = ['order']
        unique_together = ['section', 'order']

    def __str__(self):
        return f"{self.section.course.title} - {self.section.title} - {self.title}"

class LectureResource(BaseModel):
    RESOURCE_TYPE_CHOICES = [
        ('video', 'Video'),
        ('pdf', 'PDF'),
        ('link', 'Link'),
        ('document', 'Document'),
        ('image', 'Image'),
    ]
    
    PROVIDER_CHOICES = [
        ('youtube', 'YouTube'),
        ('vimeo', 'Vimeo'),
        ('self', 'Self-hosted'),
        ('drive', 'Google Drive'),
        ('dropbox', 'Dropbox'),
        ('external', 'External'),
    ]
    
    lecture = models.ForeignKey(Lecture, on_delete=models.CASCADE, related_name='resources')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    kind = models.CharField(max_length=10, choices=RESOURCE_TYPE_CHOICES, blank=True)
    resource_type = models.CharField(max_length=10, choices=RESOURCE_TYPE_CHOICES)
    url = models.URLField(max_length=500, blank=True, null=True)
    file_url = models.URLField(max_length=500, blank=True, null=True)
    external_url = models.URLField(max_length=500, blank=True, null=True)
    file = models.FileField(upload_to='lecture_resources/', blank=True, null=True)
    provider = models.CharField(max_length=10, choices=PROVIDER_CHOICES, blank=True, null=True)
    duration_seconds = models.PositiveIntegerField(blank=True, null=True)
    is_downloadable = models.BooleanField(default=False)
    file_size = models.PositiveIntegerField(blank=True, null=True)
    mime_type = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.lecture.title} - {self.title}"

    def save(self, *args, **kwargs):
        if self.resource_type and not self.kind:
            self.kind = self.resource_type
        elif self.kind and not self.resource_type:
            self.resource_type = self.kind
        
        if self.file and not any([self.url, self.file_url, self.external_url]):
            self.url = self.file.url
            self.file_url = self.file.url
        
        super().save(*args, **kwargs)

    @property
    def effective_url(self):
        return self.url or self.file_url or self.external_url or (self.file.url if self.file else None)

class QaItem(BaseModel):
    lecture = models.ForeignKey(Lecture, on_delete=models.CASCADE, related_name='qa_items')
    question = models.TextField()
    answer = models.TextField(blank=True, null=True)
    asked_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='questions_asked')
    upvotes = models.PositiveIntegerField(default=0)
    resolved = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Q: {self.question[:50]}..."

class ProjectTool(BaseModel):
    lecture = models.ForeignKey(Lecture, on_delete=models.CASCADE, related_name='project_tools')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    url = models.URLField(max_length=500)
    icon = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return self.name

class Quiz(BaseModel):
    lecture = models.ForeignKey(Lecture, on_delete=models.CASCADE, related_name='quizzes', null=True, blank=True)
    section = models.ForeignKey(CourseSection, on_delete=models.CASCADE, related_name='quizzes', null=True, blank=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='quizzes')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    instructions = models.TextField(blank=True, null=True)
    points_possible = models.PositiveIntegerField(default=10)
    due_date = models.DateTimeField(blank=True, null=True)
    is_published = models.BooleanField(default=False)
    allow_multiple_attempts = models.BooleanField(default=False)
    max_attempts = models.PositiveIntegerField(blank=True, null=True)
    time_limit_minutes = models.PositiveIntegerField(blank=True, null=True)

    def __str__(self):
        return f"{self.title} ({self.course.title})"

class QuizQuestion(BaseModel):
    QUESTION_TYPE_CHOICES = [
        ('multiple_choice', 'Multiple Choice'),
        ('true_false', 'True/False'),
        ('short_answer', 'Short Answer'),
        ('essay', 'Essay'),
    ]
    
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    question = models.TextField()
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPE_CHOICES)
    options = models.JSONField(blank=True, null=True)  # For multiple choice/true false
    correct_option_index = models.PositiveIntegerField(blank=True, null=True)
    correct_answer = models.TextField(blank=True, null=True)  # For short answer/essay
    points = models.PositiveIntegerField(default=1)
    explanation = models.TextField(blank=True, null=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.question[:50]}..."

class QuizTask(BaseModel):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    points = models.PositiveIntegerField(default=10)
    accepts_files = models.BooleanField(default=False)
    accepts_text = models.BooleanField(default=True)
    accepted_file_types = models.JSONField(blank=True, null=True)  # List of strings
    max_file_size = models.PositiveIntegerField(blank=True, null=True)  # in bytes
    max_files = models.PositiveIntegerField(blank=True, null=True)
    sample_answer = models.TextField(blank=True, null=True)
    required = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.title} ({self.quiz.title})"