import logging
import uuid
from datetime import datetime

from django.conf import settings
from django.db import models
from django.utils.dateparse import parse_datetime
from django.utils.timezone import make_aware

from floto.api import kubernetes

LOG = logging.getLogger(__name__)


class Project(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4)
    created_at = models.DateTimeField(default=datetime.now)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="pi"
    )
    name = models.CharField(max_length=200)
    description = models.CharField(max_length=2000)
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="projects",
    )

    def __str__(self):
        return f"{self.name}"


class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(deleted=None)


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
    deleted = models.DateTimeField(null=True, blank=True)

    # Overwrite the default manager to prevent ever selecting something already deleted
    objects = SoftDeleteManager()
    objects_all = models.Manager()


class Collection(CreatedByUserBase):
    name = models.CharField(max_length=200)
    description = models.CharField(max_length=2000)


class CollectionDevice(models.Model):
    collection = models.ForeignKey(
        Collection, related_name="devices", on_delete=models.CASCADE
    )
    device_uuid = models.CharField(max_length=36)


class Service(CreatedByUserBase):
    container_ref = models.CharField(max_length=1000)

    def __str__(self):
        return f"{self.container_ref} ({self.uuid})"


class ClaimableResource(models.Model):
    resource = models.CharField(max_length=100, primary_key=True)

    def __str__(self):
        return f"{self.resource}"


class ServiceClaimableResource(models.Model):
    resource = models.ForeignKey(
        ClaimableResource, related_name="services", on_delete=models.CASCADE
    )
    service = models.ForeignKey(
        Service, related_name="resources", on_delete=models.CASCADE
    )


class Application(CreatedByUserBase):
    name = models.CharField(max_length=200)
    description = models.CharField(max_length=2000)
    environment = models.JSONField()
    is_single_tenant = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class ApplicationService(models.Model):
    application = models.ForeignKey(
        Application, related_name="services", on_delete=models.CASCADE
    )
    service = models.ForeignKey(
        Service, related_name="applications", on_delete=models.CASCADE
    )


class Job(CreatedByUserBase):
    application = models.ForeignKey(Application, on_delete=models.CASCADE)
    environment = models.JSONField()
    cleaned_up = models.BooleanField(default=False)


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
    timing = models.ForeignKey(
        JobTiming,
        related_name="timeslots",
        on_delete=models.CASCADE,
        null=True,
    )

    class RelatedJobSoftDeleteManager(models.Manager):
        def get_queryset(self):
            return super().get_queryset().filter(job__deleted=None)

    objects = RelatedJobSoftDeleteManager()
    objects_all = models.Manager()


class Fleet(models.Model):
    id = models.IntegerField(primary_key=True)
    app_name = models.CharField(max_length=512)
    is_app_fleet = models.BooleanField(default=False)

    def __str__(self):
        return f"{'*' if self.is_app_fleet else ''}{self.app_name} (id: {self.id})"


class DeviceData(models.Model):
    """
    Stores our custom data on the device and filter balena API
    """

    STATUS_CHOICES = {
        ("", "--will use balena status--"),
        ("retired", "retired"),
    }

    device_uuid = models.CharField(max_length=36, primary_key=True)
    # The owner of the device.
    owner_project = models.ForeignKey(Project, on_delete=models.CASCADE)
    # Projects which can deploy to the device
    allow_all_projects = models.BooleanField(default=False)
    application_projects = models.ManyToManyField(
        Project, related_name="application_projects"
    )
    name = models.CharField(max_length=200)
    # Used to cache the fleet from balena.
    fleet = models.ForeignKey(Fleet, on_delete=models.CASCADE, null=True)
    created_at = models.DateTimeField(default=datetime.now)
    deployment_name = models.CharField(max_length=200, null=True, blank=True)
    contact = models.EmailField(max_length=254, null=True, blank=True)
    address_1 = models.CharField(max_length=128, default="", blank=True)
    address_2 = models.CharField(max_length=128, default="", blank=True)
    city = models.CharField(max_length=64, default="", blank=True)
    state = models.CharField(max_length=64, default="", blank=True)
    country = models.CharField(max_length=64, default="", blank=True)
    zip_code = models.CharField(max_length=6, default="", blank=True)
    latitude = models.DecimalField(
        max_digits=9, decimal_places=3, null=True, blank=True
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=3, null=True, blank=True
    )
    status = models.CharField(max_length=512, blank=True, choices=STATUS_CHOICES)

    # Used for update geolocation on address update
    __original_address = ""

    # Used for device CSV import
    device_update_columns = [
        "device_uuid",
        "name",
        "deployment_name",
        "contact",
        "address_1",
        "address_2",
        "city",
        "state",
        "country",
        "zip_code",
        "latitude",
        "longitude",
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__original_address = self.address()

    def __str__(self):
        return f"{self.name} ({self.device_uuid})"

    def address(self):
        return f"{self.address_1}, {self.city}, {self.state}, {self.zip_code}"

    def has_app_access(self, user, active_project=None):
        if user.is_anonymous:
            return False
        if active_project:
            return (
                self.allow_all_projects
                or active_project in self.application_projects.all()
            )
        return self.allow_all_projects or any(
            allowed_project in user.projects.all()
            for allowed_project in self.application_projects.all()
        )

    def save(self, *args, **kwargs):
        def get_lat_long(address):
            import requests

            params = {"q": address, "format": "json"}
            headers = {"User-Agent": "flotowebapp"}
            url = "https://nominatim.openstreetmap.org/search"
            LOG.info(f"Making the Nominatim Geocode API request for {address}")
            try:
                response = requests.get(url, headers=headers, params=params)
                response.raise_for_status()
                data = response.json()
                if data:
                    return float(data[0]["lat"]), float(data[0]["lon"])
            except requests.RequestException as e:
                LOG.error(f"Geocoding error for address {address} - {e}")
            return None, None

        # update lat, long only if address changed
        if self.__original_address != self.address():
            lat, long = get_lat_long(self.address())
            if lat and long:
                import random

                lat += random.uniform(-0.005, 0.005)
                long += random.uniform(-0.005, 0.005)
                self.latitude, self.longitude = lat, long
        self.__original_address = self.address()
        super(DeviceData, self).save(*args, **kwargs)


class PeripheralSchema(models.Model):
    type = models.CharField(max_length=512, primary_key=True)

    def __str__(self):
        return f"{self.type}"


class PeripheralSchemaResource(models.Model):
    label = models.CharField(max_length=512)
    count = models.IntegerField()
    schema = models.ForeignKey(
        PeripheralSchema, on_delete=models.CASCADE, related_name="resources"
    )


class PeripheralSchemaConfigItem(models.Model):
    label = models.CharField(max_length=512)
    schema = models.ForeignKey(
        PeripheralSchema, on_delete=models.CASCADE, related_name="configuration_items"
    )

    def __str__(self):
        return f"{self.schema}: {self.label}"


class Peripheral(models.Model):
    schema = models.ForeignKey(
        PeripheralSchema,
        on_delete=models.CASCADE,
    )
    name = models.CharField(max_length=512)
    documentation_url = models.CharField(max_length=1024)

    def __str__(self):
        return f"{self.schema}: {self.name}"


class PeripheralInstance(models.Model):
    peripheral = models.ForeignKey(
        Peripheral,
        on_delete=models.CASCADE,
    )
    device = models.ForeignKey(
        DeviceData,
        on_delete=models.CASCADE,
        related_name="peripherals",
    )

    def __str__(self):
        return f"{self.device} - {self.peripheral} ({self.id})"


class PeripheralConfigurationItem(models.Model):
    label = models.ForeignKey(
        PeripheralSchemaConfigItem,
        on_delete=models.CASCADE,
    )
    peripheral = models.ForeignKey(
        PeripheralInstance, on_delete=models.CASCADE, related_name="configuration"
    )
    value = models.CharField(max_length=2048)


class ServicePeripheral(models.Model):
    service = models.ForeignKey(
        Service, related_name="peripheral_schemas", on_delete=models.CASCADE
    )
    peripheral_schema = models.ForeignKey(PeripheralSchema, on_delete=models.CASCADE)


class ServicePort(models.Model):
    service = models.ForeignKey(Service, related_name="ports", on_delete=models.CASCADE)
    protocol = models.CharField(max_length=64)
    node_port = models.IntegerField()
    target_port = models.IntegerField()


class Event(models.Model):
    time = models.DateTimeField()
    timing = models.ForeignKey(
        JobTiming,
        related_name="events",
        on_delete=models.CASCADE,
    )

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        DONE = "DONE", "Done"
        ERROR = "ERROR", "Error"

    status = models.CharField(max_length=32, choices=Status.choices)

    class RelatedJobSoftDeleteManager(models.Manager):
        def get_queryset(self):
            return super().get_queryset().filter(timing__job__deleted=None)

    objects = RelatedJobSoftDeleteManager()
    objects_all = models.Manager()


class KubernetesEvent(models.Model):
    # Basically everything in kubernetes is optional, so everything is nullable
    uid = models.CharField(max_length=255, unique=True, null=True, blank=True)
    name = models.CharField(max_length=255, null=True, blank=True)
    namespace = models.CharField(max_length=255, null=True, blank=True)
    event_type = models.CharField(max_length=50, null=True, blank=True)
    reason = models.CharField(max_length=255, null=True, blank=True)
    message = models.TextField(null=True, blank=True)

    involved_object_kind = models.CharField(max_length=255, null=True, blank=True)
    involved_object_name = models.CharField(max_length=255, null=True, blank=True)
    involved_object_namespace = models.CharField(max_length=255, null=True, blank=True)
    involved_object_uid = models.CharField(max_length=255, null=True, blank=True)

    event_time = models.DateTimeField(null=True, blank=True)
    first_timestamp = models.DateTimeField(null=True, blank=True)
    last_timestamp = models.DateTimeField(null=True, blank=True)

    source_component = models.CharField(max_length=255, null=True, blank=True)
    source_host = models.CharField(max_length=255, null=True, blank=True)

    count = models.PositiveIntegerField(default=1, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    job = models.ForeignKey(
        Job, related_name="kubernetes_events", on_delete=models.CASCADE, null=True, blank=True
    )
    device = models.ForeignKey(
        DeviceData, related_name="kubernetes_events", on_delete=models.CASCADE, null=True, blank=True
    )

    def __str__(self):
        return f"{self.event_type} - {self.reason} for {self.involved_object_kind}/{self.involved_object_name}"

    class Meta:
        ordering = ['-event_time']
        verbose_name = "Kubernetes Event"
        verbose_name_plural = "Kubernetes Events"

    @classmethod
    def from_kubernetes_event(cls, event):
        def to_datetime(k8s_time):
            if not k8s_time:
                return None
            if isinstance(k8s_time, str):
                dt = parse_datetime(k8s_time)
                return make_aware(dt) if dt else None
            return make_aware(k8s_time) if not k8s_time.tzinfo else k8s_time

        try:
            job = kubernetes.get_job_from_namespace(event.metadata.namespace)
        except Exception:
            job = None

        device = None
        if event.involved_object.kind.lower() == "node":
            try:
                device = DeviceData.objects.get(pk=event.involved_object.name)
            except DeviceData.DoesNotExist:
                device = None
        elif event.involved_object.kind.lower() == "pod":
            try:
                # Look up the node for the pod
                device_pk = kubernetes.get_pod_node(event.involved_object.name, event.metadata.namespace)
                device = DeviceData.objects.get(pk=device_pk)
            except DeviceData.DoesNotExist:
                device = None

        return KubernetesEvent(
            uid=event.metadata.uid,
            name=event.metadata.name,
            namespace=event.metadata.namespace,
            event_type=event.type,
            reason=event.reason,
            message=event.message,
            involved_object_kind=event.involved_object.kind,
            involved_object_name=event.involved_object.name,
            involved_object_namespace=event.involved_object.namespace,
            involved_object_uid=event.involved_object.uid,
            event_time=to_datetime(event.event_time),
            first_timestamp=to_datetime(event.first_timestamp),
            last_timestamp=to_datetime(event.last_timestamp),
            source_component=getattr(event.source, 'component', None),
            source_host=getattr(event.source, 'host', None),
            count=event.count or 1,
            job=job,
            device=device,
        )


class Dataset(CreatedByUserBase):
    name = models.CharField(max_length=1024, unique=True)
    description = models.CharField(max_length=2000)
    url = models.CharField(max_length=1024)
    approved = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name}"


class DownloadEvent(models.Model):
    downloaded_at = models.DateTimeField(default=datetime.now)
    downloaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="downloads"
    )
    dataset = models.ForeignKey(
        Dataset,
        on_delete=models.CASCADE,
    )
