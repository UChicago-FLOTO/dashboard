# Generated by Django 4.2.9 on 2024-02-20 06:57

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("floto_api", "0013_devicedata_address_1_devicedata_address_2_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="serviceperipheral",
            name="service",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="peripheral_schemas",
                to="floto_api.service",
            ),
        ),
    ]
