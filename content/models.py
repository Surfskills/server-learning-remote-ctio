# from django.db import models
# from core.models import BaseModel
# from courses.models import Course


# class CourseSection(BaseModel):
#     course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='sections')
#     title = models.CharField(max_length=200)
#     order = models.PositiveIntegerField(default=0)

#     class Meta:
#         ordering = ['order']
#         unique_together = ['course', 'order']

#     def __str__(self):
#         return f"{self.course.title} - {self.title}"

# class Lecture(BaseModel):
#     section = models.ForeignKey(CourseSection, on_delete=models.CASCADE, related_name='lectures')
#     title = models.CharField(max_length=200)
#     order = models.PositiveIntegerField(default=0)
#     duration = models.CharField(max_length=20)  # e.g. "30m"
#     overview = models.TextField(blank=True, null=True)
#     preview_available = models.BooleanField(default=False)

#     class Meta:
#         ordering = ['order']
#         unique_together = ['section', 'order']

#     def __str__(self):
#         return f"{self.section.course.title} - {self.section.title} - {self.title}"

# class LectureResource(BaseModel):
#     RESOURCE_KIND_CHOICES = [
#         ('video', 'Video'),
#         ('pdf', 'PDF'),
#         ('link', 'Link'),
#         ('file', 'File'),
#     ]
    
#     PROVIDER_CHOICES = [
#         ('youtube', 'YouTube'),
#         ('vimeo', 'Vimeo'),
#         ('self', 'Self-hosted'),
#         ('drive', 'Google Drive'),
#         ('dropbox', 'Dropbox'),
#         ('external', 'External'),
#     ]
    
#     lecture = models.ForeignKey(Lecture, on_delete=models.CASCADE, related_name='resources')
#     title = models.CharField(max_length=200)
#     kind = models.CharField(max_length=10, choices=RESOURCE_KIND_CHOICES)
#     url = models.URLField(max_length=500)
#     provider = models.CharField(max_length=10, choices=PROVIDER_CHOICES, blank=True, null=True)
#     duration_seconds = models.PositiveIntegerField(blank=True, null=True)
#     is_downloadable = models.BooleanField(default=False)
#     file_size = models.PositiveIntegerField(blank=True, null=True)  # in bytes
#     mime_type = models.CharField(max_length=100, blank=True, null=True)

#     def __str__(self):
#         return f"{self.lecture.title} - {self.title}"