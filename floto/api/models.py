import logging
import uuid
from datetime import datetime

from django.conf import settings
from django.db import models

LOG = logging.getLogger(__name__)


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
        settings.AUTH_USER_MODEL,
        related_name="projects",
    )

    def __str__(self):
        return f"{self.name} ({self.uuid})"


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
    created_by_project = models.ForeignKey(Project, on_delete=models.CASCADE, null=True)


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


class DeviceData(models.Model):
    """
    Stores our custom data on the device and filter balena API
    """
    device_uuid = models.CharField(max_length=36, primary_key=True)
    # The owner of the device.
    owner_project = models.ForeignKey(Project, on_delete=models.CASCADE)
    # Projects which can deploy to the device
    allow_all_projects = models.BooleanField(default=False)
    application_projects = models.ManyToManyField(Project, related_name="application_projects")
    name = models.CharField(max_length=200)

    def public_dict(self, balena_device, kubernetes_node, request, active_project=None):
        """
        Combine the openbalena device, kubernetes_node, 
        and this to get the public version

        If active_project is passed, compute management/app access based on only that
        project's access. Otherwise consider any of this user's projects for access.
        """
        # TODO this should probably be refactored into a serialzier instead
        BALENA_KEYS = [
            "created_at", "modified_at", "api_heartbeat_state",
            "uuid", "device_name", "note", "is_online", "last_connectivity_event",
            "is_connected_to_vpn", "last_vpn_event",
            "memory_usage", "memory_total", "storage_usage", "storage_total",
            "cpu_usage", "cpu_temp", "is_undervolted", "status", "os_version",
            "os_variant", "supervisor_version",
        ]
        
        is_ready = False
        if kubernetes_node:
            is_ready = next(
                c for c in kubernetes_node.status.conditions
                if c.type == "Ready"
            ).status == "True"
        ip_address = [] if not balena_device.get("ip_address") else \
            [ip for ip in balena_device["ip_address"].split(" ")]
        mac_address = [] if not balena_device.get("mac_address") else \
            [mac for mac in balena_device["mac_address"].split(" ")]
        management_access = active_project == self.owner_project \
            if active_project else request.user in self.owner_project.members.all()
        return {
            "contact": self.owner_project.created_by.email,
            "management_access": management_access,
            "application_access": management_access or self.has_app_access(request.user, active_project),
            "is_ready": is_ready,
            "ip_address": ip_address,
            "mac_address": mac_address,
        } | { k: balena_device.get(k) for k in BALENA_KEYS }

    def has_app_access(self, user, active_project=None):
        if active_project:
            return self.allow_all_projects or \
                active_project in self.application_projects.all()
        return self.allow_all_projects or \
            any(
                allowed_project in user.projects.all()
                for allowed_project in self.application_projects.all()
            )