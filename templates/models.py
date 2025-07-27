from django.db import models
import uuid

from authentication.models import User

class EbookTemplate(models.Model):
    class TemplateType(models.TextChoices):
        COVER = 'COVER', 'Cover'
        CHAPTER = 'CHAPTER', 'Chapter'
        FULL = 'FULL', 'Full eBook'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    type = models.CharField(
        max_length=10,
        choices=TemplateType.choices,
        default=TemplateType.FULL
    )
    thumbnail = models.ImageField(upload_to='ebook_templates/thumbnails/')
    is_default = models.BooleanField(default=False)
    is_premium = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # For cover templates
    cover_image = models.ImageField(
        upload_to='ebook_templates/covers/',
        null=True,
        blank=True
    )
    
    # For full/chapter templates - stores CSS/HTML structure
    styles = models.JSONField(default=dict)
    structure = models.JSONField(default=dict)
    
    class Meta:
        ordering = ['-is_default', 'name']
        indexes = [
            models.Index(fields=['type']),
            models.Index(fields=['is_default']),
            models.Index(fields=['is_premium']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"
    
    def save(self, *args, **kwargs):
        # Ensure only one default template per type
        if self.is_default:
            EbookTemplate.objects.filter(
                type=self.type,
                is_default=True
            ).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)

class UserTemplate(models.Model):
    """Templates customized by users"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    base_template = models.ForeignKey(
        EbookTemplate,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    name = models.CharField(max_length=100)
    styles = models.JSONField(default=dict)
    structure = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"{self.name} (by {self.user.display_name})"