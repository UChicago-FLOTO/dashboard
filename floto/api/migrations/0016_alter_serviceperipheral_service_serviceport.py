# Generated by Django 4.2.9 on 2024-02-15 22:41

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('floto_api', '0015_devicedata_contact_alter_devicedata_address_1_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='serviceperipheral',
            name='service',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='peripheral_schemas', to='floto_api.service'),
        ),
        migrations.CreateModel(
            name='ServicePort',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('protocol', models.CharField(max_length=64)),
                ('node_port', models.IntegerField()),
                ('target_port', models.IntegerField()),
                ('service', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ports', to='floto_api.service')),
            ],
        ),
    ]