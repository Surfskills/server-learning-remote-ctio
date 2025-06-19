# signals.py - Updated and improved version

from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from authentication.models import User, Profile
# from uni_services.models import InstructorProfile  # Uncomment if you have instructor profiles
from django.db import transaction
import threading
import logging

logger = logging.getLogger(__name__)

# Thread-local storage to track signal processing
_thread_locals = threading.local()

def get_signal_processing_flag(signal_name, instance_id):
    """Get signal processing flag for current thread"""
    if not hasattr(_thread_locals, 'processing'):
        _thread_locals.processing = set()
    return f"{signal_name}_{instance_id}" in _thread_locals.processing

def set_signal_processing_flag(signal_name, instance_id, value=True):
    """Set signal processing flag for current thread"""
    if not hasattr(_thread_locals, 'processing'):
        _thread_locals.processing = set()
    
    flag = f"{signal_name}_{instance_id}"
    if value:
        _thread_locals.processing.add(flag)
    else:
        _thread_locals.processing.discard(flag)


@receiver(pre_save, sender=User)
def track_user_type_changes(sender, instance, **kwargs):
    """Track user type changes for profile cleanup"""
    if instance.pk:  # Only for existing users
        try:
            original = User.objects.get(pk=instance.pk)
            instance._original_user_type = original.user_type
        except User.DoesNotExist:
            instance._original_user_type = None
    else:
        instance._original_user_type = None


@receiver(post_save, sender=User)
def handle_user_profiles(sender, instance, created, **kwargs):
    """Create related profiles when a user is created or user_type changes"""
    
    # Prevent recursion using thread-local flag
    if get_signal_processing_flag("user_post_save", instance.pk):
        return
    
    try:
        set_signal_processing_flag("user_post_save", instance.pk, True)
        
        # Always ensure basic Profile exists
        if created:
            Profile.objects.get_or_create(user=instance)
            logger.info(f"Created basic profile for {instance.email}")

        
        # Defer profile completion calculation to avoid recursion
        transaction.on_commit(lambda: calculate_user_profile_completion_safe(instance.pk))
            
    except Exception as e:
        logger.error(f"Error in handle_user_profiles for {instance.email}: {e}")
    finally:
        set_signal_processing_flag("user_post_save", instance.pk, False)


@receiver(post_save, sender=Profile)
def handle_profile_update(sender, instance, created, **kwargs):
    """Handle profile updates to recalculate completion"""
    if not created:  # Only for updates
        # Defer profile completion calculation
        transaction.on_commit(lambda: calculate_user_profile_completion_safe(instance.user.pk))


@receiver(post_delete, sender=Profile)
def cleanup_profile_deletion(sender, instance, **kwargs):
    """Handle cleanup when profile is deleted"""
    if instance.user:
        user_pk = instance.user.pk
        transaction.on_commit(lambda: calculate_user_profile_completion_safe(user_pk))
        logger.info(f"Scheduled cleanup after profile deletion for {instance.user.email}")


def calculate_user_profile_completion_safe(user_pk):
    """Safely calculate user profile completion without triggering signals"""
    try:
        user = User.objects.select_related('profile').get(pk=user_pk)
        
        # Prevent recursion
        if get_signal_processing_flag("profile_completion", user_pk):
            return
            
        try:
            set_signal_processing_flag("profile_completion", user_pk, True)
            
            completion = 0
            total_fields = 0
            
            # Basic user fields (4 fields total)
            basic_fields = [
                bool(user.first_name),
                bool(user.last_name),
                bool(user.phone_number),
                bool(user.profile_picture),
            ]
            
            for field in basic_fields:
                total_fields += 1
                if field:
                    completion += 1
            
            # Profile fields (if profile exists)
            try:
                profile = user.profile
                profile_fields = [
                    bool(profile.bio),
                    bool(profile.location),
                    bool(profile.website),
                    bool(profile.company),
                ]
                
                for field in profile_fields:
                    total_fields += 1
                    if field:
                        completion += 1
                        
            except Profile.DoesNotExist:
                # Add profile fields as missing
                total_fields += 4
            

            
            percentage = int((completion / total_fields) * 100) if total_fields > 0 else 0
            
            # Use bulk_update to avoid triggering signals
            User.objects.filter(pk=user_pk).update(
                profile_completion_percentage=percentage,
                is_profile_complete=percentage >= 80
            )
            
            logger.debug(f"Updated profile completion for user {user.email}: {percentage}%")
            
        finally:
            set_signal_processing_flag("profile_completion", user_pk, False)
            
    except User.DoesNotExist:
        logger.warning(f"User with pk {user_pk} not found during profile completion calculation")
    except Exception as e:
        logger.error(f"Error calculating user profile completion for pk {user_pk}: {e}")



# Utility function to manually recalculate all user profile completions
def recalculate_all_profile_completions():
    """Utility function to recalculate all user profile completions"""
    logger.info("Starting bulk profile completion recalculation")
    
    for user in User.objects.all():
        try:
            calculate_user_profile_completion_safe(user.pk)
        except Exception as e:
            logger.error(f"Error recalculating profile for user {user.email}: {e}")
    
    logger.info("Completed bulk profile completion recalculation")


# Signal connection verification
def verify_signal_connections():
    """Utility function to verify signal connections"""
    from django.db.models.signals import post_save, post_delete, pre_save
    
    connections = {
        'pre_save': pre_save.receivers,
        'post_save': post_save.receivers,
        'post_delete': post_delete.receivers,
    }
    
    for signal_name, receivers in connections.items():
        logger.info(f"{signal_name} has {len(receivers)} receivers")
        for receiver in receivers:
            logger.debug(f"  - {receiver}")