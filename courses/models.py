from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.utils.text import slugify

from core.models import BaseModel
from authentication.models import User

class CourseCategory(BaseModel):
    LEVEL_CHOICES = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
        ('all_levels', 'All Levels'),
    ]
    
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

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
    
    # Support both banner_url and thumbnail for file uploads
    banner_url = models.URLField(max_length=500, blank=True, null=True)
    thumbnail = models.ImageField(upload_to='course_thumbnails/', blank=True, null=True)
    
    preview_video_url = models.URLField(max_length=500, blank=True, null=True)
    instructor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='courses_taught')
    category = models.ForeignKey(CourseCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='courses')
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default='beginner')
    language = models.CharField(max_length=10, choices=LANGUAGE_CHOICES, default='en')
    duration = models.CharField(max_length=20, blank=True, null=True)  # e.g. "5h 30m"
    rating = models.FloatField(default=0, validators=[MinValueValidator(0), MaxValueValidator(5)])
    review_count = models.PositiveIntegerField(default=0)
    students_enrolled = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)  # For archiving courses
    published_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        if self.is_published and not self.published_at:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)

    @property
    def current_price(self):
        return self.discount_price if self.discount_price else self.price

    @property
    def thumbnail_url(self):
        """Return thumbnail URL, preferring uploaded file over banner_url"""
        if self.thumbnail:
            return self.thumbnail.url
        return self.banner_url

class CourseSection(BaseModel):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='sections')
    title = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']
        unique_together = ['course', 'order']

    def __str__(self):
        return f"{self.course.title} - {self.title}"

class Lecture(BaseModel):
    section = models.ForeignKey(CourseSection, on_delete=models.CASCADE, related_name='lectures')
    title = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=0)
    duration = models.CharField(max_length=20, blank=True, null=True)  # e.g. "30m"
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
    
    # Support both 'kind' (legacy) and 'resource_type' (frontend)
    kind = models.CharField(max_length=10, choices=RESOURCE_TYPE_CHOICES, blank=True)
    resource_type = models.CharField(max_length=10, choices=RESOURCE_TYPE_CHOICES)
    
    # Support multiple URL fields for flexibility
    url = models.URLField(max_length=500, blank=True, null=True)
    file_url = models.URLField(max_length=500, blank=True, null=True)
    external_url = models.URLField(max_length=500, blank=True, null=True)
    
    # File upload support
    file = models.FileField(upload_to='lecture_resources/', blank=True, null=True)
    
    provider = models.CharField(max_length=10, choices=PROVIDER_CHOICES, blank=True, null=True)
    duration_seconds = models.PositiveIntegerField(blank=True, null=True)
    is_downloadable = models.BooleanField(default=False)
    file_size = models.PositiveIntegerField(blank=True, null=True)  # in bytes
    mime_type = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.lecture.title} - {self.title}"

    def save(self, *args, **kwargs):
        # Sync kind and resource_type fields
        if self.resource_type and not self.kind:
            self.kind = self.resource_type
        elif self.kind and not self.resource_type:
            self.resource_type = self.kind
        
        # Set URL from file upload if available
        if self.file and not any([self.url, self.file_url, self.external_url]):
            self.url = self.file.url
            self.file_url = self.file.url
        
        super().save(*args, **kwargs)

    @property
    def effective_url(self):
        """Return the most appropriate URL for this resource"""
        return self.url or self.file_url or self.external_url or (self.file.url if self.file else None)