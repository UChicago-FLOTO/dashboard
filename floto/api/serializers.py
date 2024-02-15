from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from floto.api import models
from floto.api import util
from floto.api import kubernetes
from floto.auth.models import KeycloakUser

import logging
from django.db import transaction
from django.contrib.auth.models import User


LOG = logging.getLogger(__name__)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["email"]


class CreatedByField(serializers.Field):
    def to_representation(self, value):
        return value.email

    def to_internal_value(self, data):
        # Force set created_by
        return self.context["request"].user


class CreatedByUserMeta:
    fields = "__all__"
    read_only_fields = ["uuid", "created_at", "updated_at", "created_by"]


class CreatedByUserSerializer(serializers.ModelSerializer):
    created_by = CreatedByField(default=serializers.CurrentUserDefault())
    created_by_project = serializers.PrimaryKeyRelatedField(
        queryset=models.Project.objects.all()
    )

    def validate_created_by_project(self, value):
        if not value in self.context["request"].user.projects.all():
            raise serializers.ValidationError(
                "You are not a member of that project"
            )
        return value


class ServicePeripheralSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.ServicePeripheral
        fields = ["peripheral_schema"]


class ServicePortSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.ServicePort
        fields = ["protocol", "node_port", "target_port"]


class ServiceSerializer(CreatedByUserSerializer):
    class Meta(CreatedByUserMeta):
        model = models.Service
        depth = 1
    peripheral_schemas = ServicePeripheralSerializer(many=True)
    ports = ServicePortSerializer(many=True)

    @transaction.atomic
    def create(self, validated_data):
        peripheral_schema_data = validated_data.pop("peripheral_schemas", [])
        port_data = validated_data.pop("ports", [])
        service = models.Service.objects.create(**validated_data)
        for ps in peripheral_schema_data:
            models.ServicePeripheral.objects.create(
                peripheral_schema=models.PeripheralSchema.objects.get(pk=ps["peripheral_schema"]),
                service=service,
            )
        for port in port_data:
            models.ServicePort.objects.create(
                protocol=port["protocol"],
                node_port=port["node_port"],
                target_port=port["target_port"],
                service=service,
            )
        return service


class ApplicationServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.ApplicationService
        fields = ["service"]
        read_only_fields = ["application"]


class ApplicationSerializer(CreatedByUserSerializer):
    class Meta(CreatedByUserMeta):
        model = models.Application

    @transaction.atomic
    def create(self, validated_data):
        services_data = validated_data.pop("services", [])
        application = models.Application.objects.create(**validated_data)
        for service in services_data:
            models.ApplicationService.objects.create(
                application=application,
                service=service["service"],
            )
        return application

    services = ApplicationServiceSerializer(many=True, required=False)


class CollectionDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.CollectionDevice
        fields = ["device_uuid"]
        read_only_fields = ["collection"]

    def validate_device_uuid(self, value):
        # TODO check device uuid
        return value


class CollectionSerializer(CreatedByUserSerializer):
    class Meta(CreatedByUserMeta):
        model = models.Collection

    @transaction.atomic
    def create(self, validated_data):
        devices_data = validated_data.pop("devices")
        collection = models.Collection.objects.create(**validated_data)
        for device in devices_data:
            models.CollectionDevice.objects.create(
                collection=collection,
                device_uuid=device["device_uuid"],
            )
        return collection

    devices = CollectionDeviceSerializer(many=True)


class JobDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.JobDevice
        fields = ["device_uuid"]
        read_only_fields = ["job"]

    def validate_device_uuid(self, value):
        # TODO check device uuid
        return value


class JobTimingSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.JobTiming
        fields = ["timing"]
        read_only_fields = ["job"]

    def validate_timing(self, value):
        # Just check it is valid
        util.parse_timing_string(value)
        return value


class DeviceTimeslotSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.DeviceTimeslot
        fields = ["device_uuid", "note", "start", "stop"]


class TimeslotSerializer(serializers.ModelSerializer):
    """
    This serializer is the "public" form. We do not need
    to expose the notes to a list, nor the jobs.
    """
    class Meta:
        model = models.DeviceTimeslot
        fields = ["start", "stop"]


class JobSerializer(CreatedByUserSerializer):
    class Meta(CreatedByUserMeta):
        model = models.Job

    @transaction.atomic
    def create(self, validated_data):
        devices_data = validated_data.pop("devices")
        timings_data = validated_data.pop("timings")
        with transaction.atomic():
            job = models.Job.objects.create(**validated_data)
            for device in devices_data:
                models.JobDevice.objects.create(
                    job=job,
                    device_uuid=device["device_uuid"],
                )
            for timing in timings_data:
                models.JobTiming.objects.create(
                    job=job,
                    timing=timing["timing"],
                )

        res = util.parse_timings(timings_data, devices_data)
        if res["conflicts"]:
            raise ValidationError("Could not schedule on the following devices: \n" + "\n".join(res["conflicts"].keys()), code=409)
        for device in devices_data:
            for label, timeslots in res["timeslots"].items():
                for timeslot in timeslots:
                    start = timeslot["start"]
                    stop = timeslot["stop"]

                    models.DeviceTimeslot.objects.create(
                        start=start, stop=stop,
                        device_uuid=device["device_uuid"],
                        job=job,
                        note=label,
                        category="JOB",
                    )

        kubernetes.create_deployment(devices_data, job)

        return job

    devices = JobDeviceSerializer(many=True)
    timings = JobTimingSerializer(many=True)
    application = serializers.PrimaryKeyRelatedField(
        queryset=models.Application.objects.all()
    )
    timeslots = DeviceTimeslotSerializer(many=True, read_only=True)


class UserSerializer(serializers.ModelSerializer):
    class Meta():
        model = KeycloakUser
        fields = ["email"]


class ProjectSerializer(serializers.ModelSerializer):
    class Meta():
        model = models.Project
        fields = "__all__"
        depth = 1
    members = UserSerializer(many=True)
    created_by = CreatedByField(default=serializers.CurrentUserDefault())


class PeripheralSchemaResourceSerializer(serializers.ModelSerializer):
    class Meta():
        model = models.PeripheralSchemaResource
        fields = ["label", "count"]
        depth = 1


class PeripheralSchemaConfigItemSerializer(serializers.ModelSerializer):
    class Meta():
        model = models.PeripheralSchemaConfigItem
        fields = ["id", "label"]
        depth = 1


class PeripheralSchemaSerializer(serializers.ModelSerializer):
    class Meta():
        model = models.PeripheralSchema
        fields = "__all__"
        depth = 1
    resources = PeripheralSchemaResourceSerializer(many=True)
    configuration_items = PeripheralSchemaConfigItemSerializer(many=True)


class PeripheralSerializer(serializers.ModelSerializer):
    class Meta():
        model = models.Peripheral
        fields = "__all__"
        depth = 1
    schema = PeripheralSchemaSerializer()


class DeviceSerializer(serializers.ModelSerializer):
    class Meta():
        model = models.DeviceData
        fields = [] # No fields by default

    def _device_supports_schema(self, ps, node_status_capacity):
        # For each resource in the schema, it exists on the device
        for resource in ps.resources.all():
            if resource.label not in node_status_capacity:
                return False
        return True

    def to_representation(self, instance):
        """
        Combine the openbalena device, kubernetes_node, 
        and this to get the public version

        If active_project is passed, compute management/app access based on only that
        project's access. Otherwise consider any of this user's projects for access.
        """

        balena_device = self.context["balena_device"]
        kubernetes_node = self.context["kubernetes_node"]
        request = self.context["request"]

        peripheral_schemas = self.context.get(
            "peripheral_schemas",
            models.PeripheralSchema.objects.all()
        ) 

        active_project = self.context.get("active_project", None)

        BALENA_KEYS = [
            "created_at", "modified_at", "api_heartbeat_state",
            "uuid", "device_name", "note", "is_online", "last_connectivity_event",
            "is_connected_to_vpn", "last_vpn_event",
            "memory_usage", "memory_total", "storage_usage", "storage_total",
            "cpu_usage", "cpu_temp", "is_undervolted", "status", "os_version",
            "os_variant", "supervisor_version",
        ]
        
        is_ready = False
        peripheral_resources = []
        if kubernetes_node:
            is_ready = next(
                c for c in kubernetes_node.status.conditions
                if c.type == "Ready"
            ).status == "True"

            peripheral_resources = [
                ps.type for ps in peripheral_schemas
                if self._device_supports_schema(ps, kubernetes_node.status.capacity.keys())
            ]
        ip_address = [] if not balena_device.get("ip_address") else \
            [ip for ip in balena_device["ip_address"].split(" ")]
        mac_address = [] if not balena_device.get("mac_address") else \
            [mac for mac in balena_device["mac_address"].split(" ")]
        management_access = active_project == instance.owner_project \
            if active_project else request.user in instance.owner_project.members.all()
        return {
            "contact": instance.owner_project.created_by.email,
            "management_access": management_access,
            "application_access": management_access or instance.has_app_access(request.user, active_project),
            "is_ready": is_ready,
            "ip_address": ip_address,
            "mac_address": mac_address,
            "peripherals": [
                PeripheralInstaceSerializer(p).data 
                for p in instance.peripherals.all()
            ],
            "peripheral_resources": peripheral_resources,
        } | { 
            k: balena_device.get(k) for k in BALENA_KEYS 
        } |  super().to_representation(instance)
    

class PeripheralConfigurationItemSerializer(serializers.ModelSerializer):
    class Meta():
        model = models.PeripheralConfigurationItem
        fields = [
            "value", "label"
        ]


class PeripheralInstaceSerializer(serializers.ModelSerializer):
    class Meta():
        model = models.PeripheralInstance
        fields = [
            "peripheral", "configuration", "id"
        ]
    peripheral = PeripheralSerializer()
    configuration = PeripheralConfigurationItemSerializer(many=True)