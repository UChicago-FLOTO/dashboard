# Generated by Django 4.2.6 on 2023-12-19 16:35

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("floto_api", "0006_alter_project_members_devicedata"),
    ]

    operations = [
        migrations.AddField(
            model_name="application",
            name="created_by_project",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="floto_api.project",
            ),
        ),
        migrations.AddField(
            model_name="collection",
            name="created_by_project",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="floto_api.project",
            ),
        ),
        migrations.AddField(
            model_name="job",
            name="created_by_project",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="floto_api.project",
            ),
        ),
        migrations.AddField(
            model_name="service",
            name="created_by_project",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="floto_api.project",
            ),
        ),
    ]
