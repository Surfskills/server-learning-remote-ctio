# signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import CalendarEvent, CalendarNotification
from django.utils import timezone
from datetime import timedelta

@receiver(post_save, sender=CalendarEvent)
def create_event_notifications(sender, instance, created, **kwargs):
    if created:
        # Create notifications based on user preferences
        for attendee in instance.attendees.all():
            if hasattr(attendee, 'notification_preferences'):
                prefs = attendee.notification_preferences
                for minutes in prefs.reminder_minutes:
                    if minutes > 0:
                        reminder_time = instance.start_time - timedelta(minutes=minutes)
                        if reminder_time > timezone.now():
                            CalendarNotification.objects.create(
                                event=instance,
                                user=attendee,
                                type='reminder',
                                message=f"Reminder: {instance.title} starts soon",
                                scheduled_for=reminder_time
                            )