# Generated by Django 4.2.6 on 2024-02-01 19:44

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('floto_api', '0007_application_created_by_project_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Fleet',
            fields=[
                ('id', models.IntegerField(primary_key=True, serialize=False)),
                ('app_name', models.CharField(max_length=512)),
            ],
        ),
        migrations.AddField(
            model_name='devicedata',
            name='fleet',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='floto_api.fleet'),
        ),
    ]