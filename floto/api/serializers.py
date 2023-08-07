from floto.api import models
from rest_framework import serializers


class CollectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Collection
        fields = "__all__"


class CollectionDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.CollectionDevice
        fields = "__all__"


class CreatedByUserMeta:
    fields = "__all__"
    read_only_fields = ["uuid", "created_at", "updated_at", "created_by"]


class CreatedByUserSerializer(serializers.ModelSerializer):
    created_by = serializers.PrimaryKeyRelatedField(
        read_only=True, default=serializers.CurrentUserDefault())


class ServiceSerializer(CreatedByUserSerializer):
    class Meta(CreatedByUserMeta):
        model = models.Service


class ApplicationServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.ApplicationService
        fields = ["service"]
        read_only_fields = ["application"]


class ApplicationSerializer(CreatedByUserSerializer):
    class Meta(CreatedByUserMeta):
        model = models.Application

    def create(self, validated_data):
        services_data = validated_data.pop("services")
        application = models.Application.objects.create(**validated_data)
        for service in services_data:
            models.ApplicationService.objects.create(
                application=application,
                service=service["service"],
            )
        return application

    services = ApplicationServiceSerializer(many=True)


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
        # validating timing contraints based on our spec
        return value


class JobSerializer(CreatedByUserSerializer):
    class Meta(CreatedByUserMeta):
        model = models.Job

    def create(self, validated_data):
        devices_data = validated_data.pop("devices")
        timings_data = validated_data.pop("timings")
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

        # TODO compute timeslots

        # TODO call kubernetes API from timeslots

        return job

    devices = JobDeviceSerializer(many=True)
    timings = JobTimingSerializer(many=True)
