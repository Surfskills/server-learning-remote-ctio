# Generated by Django 4.2.17 on 2025-06-25 21:50

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('planning', '0006_remove_contentreleaserule_created_by'),
    ]

    operations = [
        migrations.AddField(
            model_name='contentreleaserule',
            name='created_by',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='created_release_rules', to=settings.AUTH_USER_MODEL),
            preserve_default=False,
        ),
    ]
