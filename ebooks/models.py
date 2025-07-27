import uuid
from django.db import models
from django.core.files.storage import default_storage
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from authentication.models import User
from ebooklib import epub
from PIL import Image
import json

class EbookProject(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        PUBLISHED = 'PUBLISHED', 'Published'
        ARCHIVED = 'ARCHIVED', 'Archived'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ebooks')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.DRAFT
    )
    cover_image = models.ImageField(upload_to='ebook_covers/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    collaborators = models.ManyToManyField(
        User,
        through='EbookCollaborator',
        related_name='collaborating_ebooks'
    )
    template_styles = models.JSONField(
        default=dict,
        blank=True,
        help_text="Applied template styles (typography, colors, layout)"
    )
    template_structure = models.JSONField(
        default=dict,
        blank=True,
        help_text="Applied template structure settings"
    )
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['author']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.title} by {self.author.display_name}"

    def generate_cover_thumbnail(self):
        if not self.cover_image:
            return None
            
        try:
            with default_storage.open(self.cover_image.name, 'rb') as img_file:
                img = Image.open(img_file)
                img.thumbnail((300, 300))
                thumb_io = BytesIO()
                img.save(thumb_io, format='JPEG')
                return thumb_io.getvalue()
        except Exception as e:
            print(f"Error generating thumbnail: {e}")
            return None

class EbookCollaborator(models.Model):
    class Role(models.TextChoices):
        AUTHOR = 'AUTHOR', 'Author'
        EDITOR = 'EDITOR', 'Editor'
        REVIEWER = 'REVIEWER', 'Reviewer'

    ebook = models.ForeignKey(EbookProject, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=Role.choices)
    joined_at = models.DateTimeField(auto_now_add=True)
    can_edit = models.BooleanField(default=False)
    can_export = models.BooleanField(default=False)

    class Meta:
        unique_together = ('ebook', 'user')
        ordering = ['-joined_at']

    def __str__(self):
        return f"{self.user.display_name} as {self.role} on {self.ebook.title}"

class Chapter(models.Model):
    ebook = models.ForeignKey(
        EbookProject,
        on_delete=models.CASCADE,
        related_name='chapters'
    )
    title = models.CharField(max_length=255)
    content = models.JSONField(default=dict)  # Stores TipTap/ProseMirror JSON
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_draft = models.BooleanField(default=True)

    class Meta:
        ordering = ['order']
        indexes = [
            models.Index(fields=['ebook', 'order']),
        ]

    def __str__(self):
        return f"{self.order}. {self.title}"

class EbookExport(models.Model):
    class Format(models.TextChoices):
        PDF = 'PDF', 'PDF'
        EPUB = 'EPUB', 'EPUB'
        MOBI = 'MOBI', 'MOBI'

    ebook = models.ForeignKey(
        EbookProject,
        on_delete=models.CASCADE,
        related_name='exports'
    )
    format = models.CharField(max_length=5, choices=Format.choices)
    file = models.FileField(upload_to='ebook_exports/')
    generated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    generated_at = models.DateTimeField(auto_now_add=True)
    version = models.CharField(max_length=20)
    file_size = models.PositiveIntegerField()
    download_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-generated_at']
        get_latest_by = 'generated_at'

    def __str__(self):
        return f"{self.ebook.title} ({self.format})"