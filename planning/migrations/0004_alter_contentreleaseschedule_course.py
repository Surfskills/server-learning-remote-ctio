# Generated by Django 4.2.17 on 2025-06-25 11:33

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0001_initial'),
        ('planning', '0003_contentreleaseschedule_created_by'),
    ]

    operations = [
        migrations.AlterField(
            model_name='contentreleaseschedule',
            name='course',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='release_schedules', to='courses.course'),
        ),
    ]
