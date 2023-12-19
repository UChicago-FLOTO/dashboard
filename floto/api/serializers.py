from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from floto.api import models
from floto.api import util
from floto.api import kubernetes
from floto.auth.models import KeycloakUser

import logging
from django.conf import settings
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


class ServiceSerializer(CreatedByUserSerializer):
    class Meta(CreatedByUserMeta):
        model = models.Service
        depth = 1


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