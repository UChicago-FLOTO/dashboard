# Generated by Django 4.1.7 on 2023-08-04 19:20

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0002_application_is_public_job_is_public_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='jobdevice',
            name='device_uuid',
            field=models.CharField(default='tmp', max_length=36),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='applicationservice',
            name='application',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='services', to='api.application'),
        ),
        migrations.AlterField(
            model_name='applicationservice',
            name='service',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='applications', to='api.service'),
        ),
        migrations.AlterField(
            model_name='collectiondevice',
            name='collection_uuid',
            field=models.UUIDField(default=uuid.UUID('aba66a3b-4c55-4dc7-8a1f-f8bd80d30eef'), editable=False, primary_key=True, serialize=False),
        ),
    ]
