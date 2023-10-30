import uuid
from datetime import datetime

from django.conf import settings
from django.db import models


class CreatedByUserBase(models.Model):
    """
    Defines a class with common info for something created by a user
    """
    class Meta:
        abstract = True

    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4)
    created_at = models.DateTimeField(default=datetime.now)
    updated_at = models.DateTimeField(default=datetime.now)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    is_public = models.BooleanField(default=False)


class Collection(CreatedByUserBase):
    name = models.CharField(max_length=200)
    description = models.CharField(max_length=2000)


class CollectionDevice(models.Model):
    collection = models.ForeignKey(Collection, related_name="devices", on_delete=models.CASCADE)
    device_uuid = models.CharField(max_length=36)


class Service(CreatedByUserBase):
    container_ref = models.CharField(max_length=1000)


class Application(CreatedByUserBase):
    name = models.CharField(max_length=200)
    description = models.CharField(max_length=2000)
    environment = models.JSONField()


class ApplicationService(models.Model):
    application = models.ForeignKey(Application, related_name="services", on_delete=models.CASCADE)
    service = models.ForeignKey(Service, related_name="applications", on_delete=models.CASCADE)


class Job(CreatedByUserBase):
    application = models.ForeignKey(Application, on_delete=models.CASCADE)
    environment = models.JSONField()


class JobDevice(models.Model):
    job = models.ForeignKey(Job, related_name="devices", on_delete=models.CASCADE)
    device_uuid = models.CharField(max_length=36)


class JobTiming(models.Model):
    job = models.ForeignKey(Job, related_name="timings", on_delete=models.CASCADE)
    timing = models.CharField(max_length=2000)


class DeviceTimeslot(models.Model):
    start = models.DateTimeField()
    stop = models.DateTimeField()
    device_uuid = models.CharField(max_length=36)
    job = models.ForeignKey(Job, related_name="timeslots", on_delete=models.CASCADE)
    note = models.CharField(max_length=2000)

    class Categories(models.TextChoices):
        JOB = "JOB", "Job"
        OTHER = "OTHER", "Other"

    category = models.CharField(max_length=32, choices=Categories.choices)


class Project(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4)
    created_at = models.DateTimeField(default=datetime.now)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="pi"
    )
    name = models.CharField(max_length=200)
    description = models.CharField(max_length=2000)
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL
    )
