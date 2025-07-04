# Generated by Django 4.2.17 on 2025-06-24 13:14

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('planning', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ContentReleaseRule',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('trigger', models.CharField(choices=[('enrollment', 'Upon Enrollment'), ('date', 'Specific Date'), ('completion', 'After Previous Completion'), ('manual', 'Manual Release')], max_length=20)),
                ('offset_days', models.PositiveIntegerField(default=0)),
                ('release_date', models.DateTimeField(blank=True, null=True)),
                ('is_released', models.BooleanField(default=False)),
            ],
            options={
                'ordering': ['release_date', 'offset_days'],
            },
        ),
        migrations.CreateModel(
            name='ContentReleaseSchedule',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('strategy', models.CharField(choices=[('fixed_dates', 'Fixed Dates'), ('relative_enrollment', 'Relative to Enrollment'), ('self_paced', 'Self-Paced'), ('drip', 'Drip Content')], max_length=20)),
                ('start_date', models.DateTimeField(blank=True, null=True)),
                ('end_date', models.DateTimeField(blank=True, null=True)),
                ('unlock_all', models.BooleanField(default=False)),
                ('days_between_releases', models.PositiveIntegerField(blank=True, null=True)),
                ('release_time', models.TimeField(default='00:00:00')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='StudentProgressOverride',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('override_date', models.DateTimeField(blank=True, null=True)),
                ('is_released', models.BooleanField(default=False)),
                ('notes', models.TextField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='UserCalendarSettings',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('default_view', models.CharField(choices=[('day', 'Day'), ('week', 'Week'), ('month', 'Month'), ('agenda', 'Agenda')], default='week', max_length=20)),
                ('time_zone', models.CharField(default='UTC', max_length=50)),
                ('working_hours_start', models.TimeField(default='09:00:00')),
                ('working_hours_end', models.TimeField(default='17:00:00')),
                ('default_event_duration', models.PositiveIntegerField(default=60)),
                ('enable_email_notifications', models.BooleanField(default=True)),
                ('enable_push_notifications', models.BooleanField(default=True)),
                ('reminder_minutes_before', models.JSONField(default=list)),
                ('color_scheme', models.CharField(default='default', max_length=20)),
                ('show_week_numbers', models.BooleanField(default=False)),
                ('first_day_of_week', models.PositiveIntegerField(choices=[(0, 'Day 0'), (1, 'Day 1'), (2, 'Day 2'), (3, 'Day 3'), (4, 'Day 4'), (5, 'Day 5'), (6, 'Day 6')], default=0)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.RemoveField(
            model_name='calendarpermissions',
            name='user',
        ),
        migrations.RemoveField(
            model_name='dripschedule',
            name='course',
        ),
        migrations.RemoveField(
            model_name='dripscheduleentry',
            name='lecture',
        ),
        migrations.RemoveField(
            model_name='dripscheduleentry',
            name='schedule',
        ),
        migrations.RemoveField(
            model_name='dripscheduleentry',
            name='section',
        ),
        migrations.AlterUniqueTogether(
            name='plannedcourserelease',
            unique_together=None,
        ),
        migrations.RemoveField(
            model_name='plannedcourserelease',
            name='course',
        ),
        migrations.RemoveField(
            model_name='plannedcourserelease',
            name='lecture',
        ),
        migrations.RemoveField(
            model_name='plannedcourserelease',
            name='related_event',
        ),
        migrations.RemoveField(
            model_name='plannedcourserelease',
            name='section',
        ),
        migrations.RemoveField(
            model_name='plannedcourserelease',
            name='student',
        ),
        migrations.AlterUniqueTogether(
            name='studentprogresscontrol',
            unique_together=None,
        ),
        migrations.RemoveField(
            model_name='studentprogresscontrol',
            name='course',
        ),
        migrations.RemoveField(
            model_name='studentprogresscontrol',
            name='locked_lectures',
        ),
        migrations.RemoveField(
            model_name='studentprogresscontrol',
            name='student',
        ),
        migrations.RemoveField(
            model_name='studentprogresscontrol',
            name='unlocked_lectures',
        ),
        migrations.RenameField(
            model_name='calendarevent',
            old_name='related_lecture',
            new_name='lecture',
        ),
        migrations.RemoveField(
            model_name='calendarnotification',
            name='type',
        ),
        migrations.AddField(
            model_name='calendarevent',
            name='color',
            field=models.CharField(default='#3b82f6', max_length=20),
        ),
        migrations.AddField(
            model_name='calendarevent',
            name='course_event_type',
            field=models.CharField(blank=True, choices=[('release', 'Content Release'), ('live_session', 'Live Session'), ('quiz', 'Quiz'), ('lecture', 'Lecture'), ('exam', 'Exam')], max_length=20, null=True),
        ),
        migrations.AddField(
            model_name='calendarevent',
            name='is_recurring',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='calendarevent',
            name='recurrence_pattern',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='calendarevent',
            name='section',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='events', to='courses.coursesection'),
        ),
        migrations.AddField(
            model_name='calendarnotification',
            name='delivery_method',
            field=models.CharField(choices=[('email', 'Email'), ('push', 'Push Notification'), ('both', 'Email and Push')], default='both', max_length=10),
        ),
        migrations.AddField(
            model_name='calendarnotification',
            name='notification_type',
            field=models.CharField(choices=[('reminder', 'Reminder'), ('update', 'Update'), ('cancellation', 'Cancellation'), ('new_event', 'New Event')], default=2, max_length=20),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='calendarnotification',
            name='sent_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='calendarevent',
            name='course',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='calendar_events', to='courses.course'),
        ),
        migrations.AlterField(
            model_name='calendarevent',
            name='event_type',
            field=models.CharField(choices=[('course', 'Course Related'), ('personal', 'Personal'), ('meeting', 'Meeting'), ('reminder', 'Reminder'), ('deadline', 'Deadline')], max_length=20),
        ),
        migrations.AlterField(
            model_name='calendarevent',
            name='priority',
            field=models.CharField(choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('critical', 'Critical')], default='medium', max_length=10),
        ),
        migrations.AlterField(
            model_name='calendarevent',
            name='status',
            field=models.CharField(choices=[('scheduled', 'Scheduled'), ('completed', 'Completed'), ('cancelled', 'Cancelled'), ('postponed', 'Postponed')], default='scheduled', max_length=20),
        ),
        migrations.AddIndex(
            model_name='calendarevent',
            index=models.Index(fields=['start_time', 'end_time'], name='planning_ca_start_t_1dfb7c_idx'),
        ),
        migrations.AddIndex(
            model_name='calendarevent',
            index=models.Index(fields=['course', 'section', 'lecture'], name='planning_ca_course__ad1f23_idx'),
        ),
        migrations.AddIndex(
            model_name='calendarnotification',
            index=models.Index(fields=['event', 'user'], name='planning_ca_event_i_f3e579_idx'),
        ),
        migrations.AddIndex(
            model_name='calendarnotification',
            index=models.Index(fields=['scheduled_for', 'sent'], name='planning_ca_schedul_b57618_idx'),
        ),
        migrations.DeleteModel(
            name='CalendarPermissions',
        ),
        migrations.DeleteModel(
            name='DripSchedule',
        ),
        migrations.DeleteModel(
            name='DripScheduleEntry',
        ),
        migrations.DeleteModel(
            name='PlannedCourseRelease',
        ),
        migrations.DeleteModel(
            name='StudentProgressControl',
        ),
        migrations.AddField(
            model_name='usercalendarsettings',
            name='user',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='calendar_settings', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='studentprogressoverride',
            name='rule',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='planning.contentreleaserule'),
        ),
        migrations.AddField(
            model_name='studentprogressoverride',
            name='student',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='progress_overrides', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='contentreleaseschedule',
            name='course',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='release_schedule', to='courses.course'),
        ),
        migrations.AddField(
            model_name='contentreleaserule',
            name='lecture',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='courses.lecture'),
        ),
        migrations.AddField(
            model_name='contentreleaserule',
            name='quiz',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='courses.quiz'),
        ),
        migrations.AddField(
            model_name='contentreleaserule',
            name='release_event',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='planning.calendarevent'),
        ),
        migrations.AddField(
            model_name='contentreleaserule',
            name='schedule',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='rules', to='planning.contentreleaseschedule'),
        ),
        migrations.AddField(
            model_name='contentreleaserule',
            name='section',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='courses.coursesection'),
        ),
        migrations.AlterUniqueTogether(
            name='studentprogressoverride',
            unique_together={('student', 'rule')},
        ),
        migrations.AlterUniqueTogether(
            name='contentreleaserule',
            unique_together={('schedule', 'section', 'lecture', 'quiz')},
        ),
    ]
