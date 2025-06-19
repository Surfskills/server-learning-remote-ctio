from django.db import models
import uuid

class BaseModel(models.Model):
    """
    Abstract base model with common fields
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class HealthCheck(models.Model):
    """
    Model to track system health status
    """
    service_name = models.CharField(max_length=100)
    status = models.BooleanField(default=True)
    last_checked = models.DateTimeField(auto_now=True)
    response_time = models.FloatField(help_text="Response time in milliseconds")
    details = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"{self.service_name} - {'Healthy' if self.status else 'Unhealthy'}"