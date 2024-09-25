# Generated by Django 5.1.1 on 2024-09-25 15:00

import django.contrib.gis.db.models.fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="speedrecord",
            name="location",
            field=django.contrib.gis.db.models.fields.PointField(
                geography=True, null=True, srid=4326
            ),
        ),
    ]