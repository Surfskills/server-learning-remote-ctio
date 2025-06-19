from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import UserProfile, UserPreference

User = get_user_model()

@receiver(post_save, sender=User)
def create_user_extended_profile(sender, instance, created, **kwargs):
    """
    Create extended profile and preferences when a new user is created
    """
    if created:
        UserProfile.objects.get_or_create(user=instance)
        UserPreference.objects.get_or_create(user=instance)