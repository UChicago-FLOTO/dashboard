from collections import defaultdict
import json
from urllib import response

from django.conf import settings
from django.http import Http404
from django.db.models import Q
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from drf_spectacular.helpers import forced_singular_serializer
import base64
import logging
import ssl
import socket
import paramiko
from datetime import datetime

from floto.api.models import (
    DeviceData,
    Peripheral,
    PeripheralConfigurationItem,
    PeripheralInstance,
    PeripheralSchema,
    PeripheralSchemaConfigItem,
    Project,
    Collection,
)
from floto.api.openapi import (
    InlineDeviceSerializer,
    device_filter_param,
    InlineActionSerializer,
    EmptyResponseSerializer,
    InlineLogSerializer,
    InlineCommandSerializer,
    InlineCommandResponseSerializer,
    InlineEnvironmentVariableSerializer,
    obj_with_owner_filter_param,
    InlineJobEventSerializer,
    InlineJobLogSerializer,
    InlineJobCheckSerializer,
    InlineCollectionSerializer,
    uuid_param,
    logs_count_param,
    InlineProjectSerializer,
    InlineWrappedProjectSerializer,
    TimeslotSummarySerializer,
    from_param,
    to_param,
)
from floto.auth.models import KeycloakUser

from .balena import get_balena_client
from balena import exceptions

from floto.api import filters, permissions
from floto.api.serializers import (
    ClaimableResourceSerializer,
    DeviceSerializer,
    PeripheralSchemaSerializer,
    PeripheralSerializer,
    ProjectSerializer,
    ServiceSerializer,
    ApplicationSerializer,
    JobSerializer,
    CollectionSerializer,
    TimeslotSerializer,
    PeripheralInstaceSerializer,
    DatasetSerializer,
)
from floto.api import util
from floto.api.models import CollectionDevice
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework import filters as drf_filters
from rest_framework.response import Response
from rest_framework import status

from floto.api import kubernetes

LOG = logging.getLogger(__name__)


@extend_schema_view(
    list=extend_schema(
        description="List all devices",
        responses=InlineDeviceSerializer,
        parameters=[device_filter_param],
    ),
    retrieve=extend_schema(
        description="Retrieve the information of a device for a specific device.",
        responses=InlineDeviceSerializer,
        parameters=[uuid_param, device_filter_param],
    ),
    logs=extend_schema(
        description="Fetch the logs of the FLOTO framework from the device. This does not fetch the logs of the applications running on the device, but can be used to inform why the device is not `ready`.",
        responses=InlineLogSerializer,
        parameters=[uuid_param, logs_count_param],
    ),
    device_action=extend_schema(
        description="Perform an action on the device",
        request=InlineActionSerializer,
        responses=EmptyResponseSerializer,
        parameters=[uuid_param],
    ),
    device_peripherals=extend_schema(
        description="Configure a peripheral on the device, either for a new peripheral, or from an existing parameter if `peripheral_id` is given.",
        request=PeripheralInstaceSerializer,
        responses=PeripheralInstaceSerializer,
        parameters=[
            uuid_param,
            OpenApiParameter(
                name="p_id",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                required=True,
                description="The peripheral's ID.",
            ),
        ],
    ),
    device_peripheral_delete=extend_schema(
        description="Deletes a peripheral from this device.",
        parameters=[
            uuid_param,
            OpenApiParameter(
                name="p_id",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                required=True,
                description="The peripheral's ID.",
            ),
        ],
    ),
    command=extend_schema(
        description="Runs a command on the device OS. Requires the device to be connected to the VPN.",
        request=InlineCommandSerializer,
        responses=InlineCommandResponseSerializer,
        parameters=[uuid_param],
    ),
    environment_retrieve=extend_schema(
        description="Fetch the configured environment variables for the device.",
        responses=InlineEnvironmentVariableSerializer,
        parameters=[uuid_param],
    ),
)
class DeviceViewSet(viewsets.ViewSet):
    serializer_class = DeviceSerializer

    # Though this is not a ModelViewSet, we implement a
    # similar filter concept.
    device_filters = [filters.DeviceFilter()]

    permission_classes = [
        permissions.MethodAllowed,
        permissions.DevicePermission,
    ]

    @staticmethod
    def filter(request, devices, view):
        res = devices
        for f in DeviceViewSet.device_filters:
            res = f.filter_queryset(request, res, view)
        return res

    def list(self, request):
        balena = get_balena_client()
        res = DeviceViewSet.filter(request, balena.models.device.get_all(), self)
        return Response(res)

    def retrieve(self, request, pk):
        balena = get_balena_client()
        res = DeviceViewSet.filter(request, [balena.models.device.get(pk)], self)
        # Note we are essentially just checking this device
        # was not filtered out entirely
        if res:
            return Response(res[0])
        else:
            raise Http404

    @action(
        detail=True,
        url_path=r"logs/(?P<count>[^/.]+)",
        permission_classes=permission_classes,
    )
    def logs(self, request, pk, count):
        balena = get_balena_client()
        res = balena.logs.history(pk, count)
        return Response(res)

    @action(methods=["POST"], detail=True, url_path="action")
    def device_action(self, request, pk):
        data = json.loads(request.data)
        device_action = data["action"]
        balena = get_balena_client()
        if device_action == "RESTART":
            balena.models.device.reboot(uuid_or_id=pk, force=True)
        elif device_action == "BLINK":
            balena.models.device.identify(uuid_or_id=pk)
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        return Response(status=status.HTTP_200_OK)

    @action(methods=["DELETE"], detail=True, url_path=r"peripherals/(?P<p_id>[^/.]+)")
    def device_peripheral_delete(self, request, pk, p_id):
        """
        Deletes the given peripheral from this device
        """
        PeripheralInstance.objects.get(pk=p_id).delete()
        return Response(status=204)

    @action(methods=["PATCH"], detail=True, url_path="peripherals")
    def device_peripherals(self, request, pk):
        data = request.data
        peripheral_instance = None
        if data.get("peripheral_id"):
            peripheral_instance = PeripheralInstance.objects.create(
                peripheral=Peripheral.objects.get(pk=data["peripheral_id"]),
                device=DeviceData.objects.get(pk=pk),
            )
        else:
            peripheral = Peripheral.objects.create(
                name=data["peripheral"]["name"],
                documentation_url=data["peripheral"]["documentation_url"],
                schema=PeripheralSchema.objects.get(
                    pk=data["peripheral"]["schema"]["type"]
                ),
            )
            peripheral_instance = PeripheralInstance.objects.create(
                peripheral=peripheral,
                device=DeviceData.objects.get(pk=pk),
            )
        for item in data["configuration"]:
            PeripheralConfigurationItem.objects.create(
                peripheral=peripheral_instance,
                label=PeripheralSchemaConfigItem.objects.get(pk=item["label"]),
                value=item["value"],
            )
        return Response(PeripheralInstaceSerializer(peripheral_instance).data)

    @action(methods=["POST"], detail=True, url_path="command")
    def command(self, request, pk):
        balena = get_balena_client()
        jwt = balena.settings.get("token")
        command = request.POST["command"]
        ssh_port = settings.BALENA_TUNNEL_PORT
        encoded_auth = base64.b64encode(f"admin:{jwt}".encode("utf-8")).decode("utf-8")
        headers = [
            f"CONNECT {pk}.balena:{ssh_port} HTTP/1.0",
            f"Proxy-Authorization: Basic {encoded_auth}",
        ]
        context = ssl.create_default_context()
        hostname = settings.BALENA_TUNNEL_HOST
        res = {}
        with socket.create_connection((hostname, 443)) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                ssock.sendall(("\r\n".join(headers) + "\r\n\r\n").encode("utf-8"))
                # Need to read http res before passing to SSH client
                sock_res = ssock.recv(1024)
                if not sock_res.decode("utf-8").startswith(
                    "HTTP/1.0 200 Connection Established"
                ):
                    raise Exception("Could not establish connect")

                ssh_client = paramiko.client.SSHClient()
                ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                pkey = paramiko.RSAKey.from_private_key_file("/config/keys/id_rsa")
                ssh_client.connect("", username="root", pkey=pkey, sock=ssock)
                _, stdout, stderr = ssh_client.exec_command(command, get_pty=True)

                stdout_str = ""
                for line in iter(stdout.readline, ""):
                    stdout_str += line
                res["stdout"] = stdout_str

                stderr_str = ""
                for line in iter(stderr.readline, ""):
                    stderr_str += line
                res["stderr"] = stderr_str
        return Response(res)

    @action(methods=["GET"], detail=True, url_path="environment")
    def environment_retrieve(self, request, pk):
        balena = get_balena_client()
        env = balena.models.device.env_var.get_all_by_device(uuid_or_id=pk)
        return Response(env, status=status.HTTP_200_OK)


@extend_schema_view(
    list=extend_schema(
        parameters=[obj_with_owner_filter_param],
    ),
    retrieve=extend_schema(
        parameters=[obj_with_owner_filter_param, uuid_param],
    ),
    destroy=extend_schema(
        parameters=[uuid_param],
    ),
)
class ModelWithOwnerViewSet(viewsets.ModelViewSet):
    destroy_permission_classes = [permissions.IsOwnerOfObject]
    http_method_names = ["get", "post", "delete"]
    filter_backends = [
        filters.HasReadAccessFilterBackend,
        drf_filters.OrderingFilter,
    ]
    ordering = ["created_at"]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({"request": self.request})
        return context

    def get_queryset(self):
        return self.serializer_class.Meta.model.objects.filter(deleted=None)

    def get_permissions(self):
        action_permissions = []
        if self.action in ("destroy", "unassign"):
            action_permissions = self.destroy_permission_classes
        return (
            super(ModelWithOwnerViewSet, self).get_permissions()
            + [permission() for permission in action_permissions]
            + [permissions.MethodAllowed()]
        )

    def perform_destroy(self, obj):
        """
        Soft-delete only
        """
        obj.deleted = datetime.now()
        obj.save()


@extend_schema_view(
    list=extend_schema(description="List all services."),
    create=extend_schema(description="Create a service."),
    retrieve=extend_schema(description="Gets a service by ID."),
    destroy=extend_schema(
        description="Deletes a service. Only permitted for the owner of the service."
    ),
)
class ServiceViewSet(ModelWithOwnerViewSet):
    serializer_class = ServiceSerializer

@extend_schema_view(
    list=extend_schema(description="List all applications."),
    create=extend_schema(description="Create an application."),
    retrieve=extend_schema(description="Gets an application by ID."),
    destroy=extend_schema(
        description="Deletes an application. Only permitted for the owner of the application."
    ),
)
class ApplicationViewSet(ModelWithOwnerViewSet):
    serializer_class = ApplicationSerializer

@extend_schema_view(
    list=extend_schema(description="List all jobs."),
    create=extend_schema(description="Create a job."),
    retrieve=extend_schema(description="Gets a job."),
    destroy=extend_schema(
        description="Deletes a job. Only permitted for the owner of the job."
    ),
    events=extend_schema(
        description="Fetch events related to the deployment of this job.",
        responses=InlineJobEventSerializer,
        parameters=[uuid_param],
    ),
    logs=extend_schema(
        description="Logs per container, per device for this job.",
        responses=InlineJobLogSerializer,
        parameters=[uuid_param],
    ),
    check=extend_schema(
        description="Check if a job with the given devices and timings can be created without issues. If `conflicts` is not empty, job creation would fail. Conflicts may occur if scheduling the job would cause collisions with peripherals, ports, or single-tenancy with jobs already scheduled.",
        responses=InlineJobCheckSerializer,
    ),
)
class JobViewSet(ModelWithOwnerViewSet):
    serializer_class = JobSerializer

    @action(methods=["GET"], detail=True, url_path="events")
    def events(self, request, pk):
        event_list = kubernetes.get_job_events(pk)
        return Response(event_list, status=status.HTTP_200_OK)

    @action(methods=["GET"], detail=True, url_path="logs")
    def logs(self, request, pk):
        return Response(kubernetes.get_job_logs(pk))

    def perform_destroy(self, job):
        if not settings.KUBE_READ_ONLY:
            kubernetes.destroy_job(job)
            job.cleaned_up = True
            job.save()
        super().perform_destroy(job)

    @action(methods=["POST"], detail=False, url_path="check")
    def check(self, request):
        """
        Check if a job with the given devices and timings can be created without issues.
        Returns 200 if check is successful.
        """
        return Response(
            util.parse_timings(
                request.data["timings"],
                request.data["devices"],
                request.data["application"]["uuid"],
            )
        )


@extend_schema_view(
    list=extend_schema(description="List all collections."),
    create=extend_schema(description="Create a collection."),
    retrieve=extend_schema(description="Gets a collection by ID."),
    destroy=extend_schema(
        description="Deletes a collection. Only permitted for the owner of the collection."
    ),
    partial_update=extend_schema(
        description="Update collection devices.",
        responses=InlineCollectionSerializer,
        parameters=[uuid_param],
    ),
)
class CollectionViewSet(ModelWithOwnerViewSet):
    serializer_class = CollectionSerializer
    http_method_names = ["get", "post", "patch", "delete"]

    def partial_update(self, request, pk, format=None):
        devices = set(m["device_uuid"] for m in request.data.pop("devices"))
        collection = Collection.objects.get(pk=pk)
        existing_devices = set(m.device_uuid for m in collection.devices.all())
        to_add = devices - existing_devices
        to_remove = existing_devices - devices
        for uuid in to_add:
            CollectionDevice.objects.create(
                collection=collection,
                device_uuid=uuid,
            )
        for uuid in to_remove:
            CollectionDevice.objects.filter(
                collection=collection,
                device_uuid=uuid,
            ).all().delete()
        collection.save()
        return Response(CollectionSerializer(collection).data)


@extend_schema_view(
    list=extend_schema(
        responses=forced_singular_serializer(TimeslotSummarySerializer),
        parameters=[from_param, to_param],
        description="For every device with a claimed timeslot, gets a list of those timeslots.",
    )
)
class TimeslotViewSet(viewsets.ViewSet):
    def list(self, request):
        object_manager = TimeslotSerializer.Meta.model.objects

        from_str = request.query_params.get("from")
        if from_str:
            from_date = util.parse_javascript_iso_string(from_str)
            if from_date:
                object_manager = object_manager.filter(stop__gte=from_date)

        to_str = request.query_params.get("to")
        if to_str:
            to_date = util.parse_javascript_iso_string(to_str)
            if to_date:
                object_manager = object_manager.filter(start__lte=to_date)

        timeslots_by_devices = defaultdict(list)
        for obj in object_manager.all():
            ts = TimeslotSerializer(obj)
            timeslots_by_devices[obj.device_uuid].append(ts.data)
        return Response(timeslots_by_devices)


@extend_schema_view(
    list=extend_schema(
        description="List all projects the current user is a member of.",
    ),
    retrieve=extend_schema(
        description="Retrieve the information of a specific project.",
        parameters=[uuid_param],
    ),
    partial_update=extend_schema(
        description="Set the membership list of a project.",
        request=InlineProjectSerializer,
        parameters=[uuid_param],
        responses=InlineWrappedProjectSerializer,
    ),
)
class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    http_method_names = ["get", "post", "patch"]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({"request": self.request})
        return context

    def get_queryset(self):
        return Project.objects.filter(
            Q(created_by=self.request.user) | Q(members=self.request.user)
        ).distinct()

    def partial_update(self, request, pk, format=None):
        # TODO this only allows patching members right now. We may want to add
        # updating name/description/PI
        errors = []
        members = set(m["email"] for m in request.data.pop("members"))
        project = Project.objects.get(pk=pk)
        existing_members = set(m.email for m in project.members.all())
        to_add = members - existing_members
        to_remove = existing_members - members
        for email in to_add:
            user = KeycloakUser.objects.filter(email=email).first()
            if user:
                project.members.add(user)
            else:
                errors.append(f"Could not find user '{email}'")
        for email in to_remove:
            # NOTE we don't check if user exists here, since we got it
            # from the project FK
            user = KeycloakUser.objects.filter(email=email).first()
            project.members.remove(user)
        project.save()
        return Response(
            {
                "project": ProjectSerializer(project).data,
                "errors": errors,
            }
        )


@extend_schema_view(
    list=extend_schema(
        description="List all peripheral schemas",
    ),
    retrieve=extend_schema(
        description="Retrieve the information of a specific peripheral schema.",
        parameters=[uuid_param],
    ),
)
class PeripheralSchemaViewSet(viewsets.ModelViewSet):
    serializer_class = PeripheralSchemaSerializer
    http_method_names = ["get"]

    def get_queryset(self):
        return self.serializer_class.Meta.model.objects.all()


class PeripheralViewSet(viewsets.ModelViewSet):
    serializer_class = PeripheralSerializer
    http_method_names = ["get"]

    def get_queryset(self):
        return self.serializer_class.Meta.model.objects.all()


@extend_schema_view(
    list=extend_schema(
        description="List all types of claimable resource",
    ),
    retrieve=extend_schema(
        description="Retrieve the information of a specific claimable resource.",
        parameters=[uuid_param],
    ),
)
class ClaimableResourceViewSet(viewsets.ModelViewSet):
    serializer_class = ClaimableResourceSerializer
    http_method_names = ["get"]

    def get_queryset(self):
        return self.serializer_class.Meta.model.objects.all()

@extend_schema_view(
    list=extend_schema(
        description="List all approved datasets",
    ),
    retrieve=extend_schema(
        description="Retrieve the information of a specific dataset.",
        parameters=[uuid_param],
    ),
    create=extend_schema(description="Create a dataset."),
)
class DatasetViewSet(viewsets.ModelViewSet):
    serializer_class = DatasetSerializer
    http_method_names = ["get", "post"]

    def get_queryset(self):
        return self.serializer_class.Meta.model.objects.filter(approved=True)
