# Generated by Django 4.2.17 on 2025-06-22 04:06

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='HealthCheck',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('service_name', models.CharField(max_length=100)),
                ('status', models.BooleanField(default=True)),
                ('last_checked', models.DateTimeField(auto_now=True)),
                ('response_time', models.FloatField(help_text='Response time in milliseconds')),
                ('details', models.JSONField(blank=True, default=dict)),
            ],
        ),
    ]
