from collections import defaultdict
import json

import django.core.serializers
from django.conf import settings
from django.core import serializers
import base64
import logging
import ssl
import socket
import paramiko

from .balena import get_balena_client
from balena import exceptions

from floto.api import permissions
from floto.api.serializers import (
    ServiceSerializer,
    ApplicationSerializer,
    JobSerializer,
    CollectionSerializer,
    TimeslotSerializer,
)
from floto.api import util
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status

from floto.api import kubernetes

LOG = logging.getLogger(__name__)


class DeviceViewSet(viewsets.ViewSet):
    def list(self, request):
        balena = get_balena_client()
        res = balena.models.device.get_all()
        return Response(res)

    def retrieve(self, request, pk):
        balena = get_balena_client()
        res = balena.models.device.get(pk)
        return Response(res)

    @action(detail=True, url_path=r'logs/(?P<count>[^/.]+)')
    def logs(self, request, pk, count):
        balena = get_balena_client()
        res = balena.logs.history(pk, count)
        return Response(res)

    @action(methods=["POST"], detail=True, url_path="action")
    def device_action(self, request, pk):
        data = json.loads(request.data)
        device_action = data['action']
        balena = get_balena_client()
        if device_action == 'RESTART':
            balena.models.device.reboot(uuid_or_id=pk, force=True)
        elif device_action == 'BLINK':
            balena.models.device.identify(uuid_or_id=pk)
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        return Response(status=status.HTTP_200_OK)

    @action(methods=["POST"], detail=True, url_path="command")
    def command(self, request, pk):
        balena = get_balena_client()
        jwt = balena.settings.get("token")
        command = request.POST["command"]
        ssh_port = settings.BALENA_TUNNEL_PORT
        encoded_auth = base64.b64encode(
            f'admin:{jwt}'.encode("utf-8")).decode("utf-8")
        headers = [
            f"CONNECT {pk}.balena:{ssh_port} HTTP/1.0",
            f"Proxy-Authorization: Basic {encoded_auth}",
        ]
        context = ssl.create_default_context()
        hostname = settings.BALENA_TUNNEL_HOST
        res = {}
        with socket.create_connection((hostname, 443)) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                ssock.sendall(
                    ("\r\n".join(headers) + '\r\n\r\n').encode("utf-8"))
                # Need to read http res before passing to SSH client
                sock_res = ssock.recv(1024)
                if not sock_res.decode("utf-8").startswith(
                        "HTTP/1.0 200 Connection Established"):
                    raise Exception("Could not establish connect")

                ssh_client = paramiko.client.SSHClient()
                ssh_client.set_missing_host_key_policy(
                    paramiko.AutoAddPolicy())
                pkey = paramiko.RSAKey.from_private_key_file(
                    "/config/keys/id_rsa")
                ssh_client.connect(
                    "", username="root", pkey=pkey, sock=ssock)
                _, stdout, stderr = ssh_client.exec_command(
                    command, get_pty=True)

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


class FleetViewSet(viewsets.ViewSet):
    def list(self, request):
        balena = get_balena_client()
        res = balena.models.application.get_all()
        return Response(res)

    @action(detail=True, url_path=r'releases/')
    def releases(balena, request, pk):
        try:
            balena = get_balena_client()
            res = balena.models.release.get_all_by_application(pk)
            return Response(res)
        except exceptions.ReleaseNotFound:
            return Response([])

    @action(methods=["POST"], detail=True, url_path=r'releases/(?P<release_ref>[^/.]+)/note')
    def note(self, request, pk, release_ref):
        balena = get_balena_client()
        balena.models.release.set_note(release_ref, request.POST["note"])
        return Response({"status": "OK"})


class EnvViewSet(viewsets.ViewSet):
    def destroy(self, request, pk):
        client = get_balena_client()
        env_key = request.query_params.get('env_key')
        client.models.device.env_var.remove(uuid_or_id=pk, key=env_key)
        return Response(status=status.HTTP_200_OK)

    def create(self, request):
        client = get_balena_client()
        data = json.loads(request.data)
        uuid = data.pop('uuid')
        for key, value in data.items():
            client.models.device.env_var.set(uuid, env_var_name=key, value=value)
        return Response(status=status.HTTP_200_OK)


class ModelWithOwnerViewSet(viewsets.ModelViewSet):
    destroy_permision_classes = [permissions.IsOwnerOfObject]
    http_method_names = ["get", "post", "delete"]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({"request": self.request})
        return context

    def get_queryset(self):
        return util.filter_by_created_by_or_public(
            self.serializer_class.Meta.model.objects, self.request)

    def get_permissions(self):
        action_permissions = []
        if self.action in ("destroy", "unassign"):
            action_permissions = self.destroy_permision_classes
        return super(ModelWithOwnerViewSet, self).get_permissions() + [
            permission() for permission in action_permissions
        ]


class ServiceViewSet(ModelWithOwnerViewSet):
    serializer_class = ServiceSerializer


class ApplicationViewSet(ModelWithOwnerViewSet):
    serializer_class = ApplicationSerializer


class JobViewSet(ModelWithOwnerViewSet):
    serializer_class = JobSerializer

    @action(methods=["GET"], detail=True, url_path="events")
    def events(self, request, pk):
        event_list = kubernetes.get_job_events(pk)
        return Response(event_list, status=status.HTTP_200_OK)


class CollectionViewSet(ModelWithOwnerViewSet):
    serializer_class = CollectionSerializer


class TimeslotViewSet(viewsets.ViewSet):
    def list(self, request):
        timeslots_by_devices = defaultdict(list)
        for obj in TimeslotSerializer.Meta.model.objects.all():
            ts = TimeslotSerializer(obj)
            timeslots_by_devices[obj.device_uuid].append(ts.data)
        return Response(timeslots_by_devices)

    @action(methods=["POST"], detail=False, url_path="check")
    def check(self, request):
        return Response(
            util.parse_timings(
                request.data["timings"], request.data["devices"]
            )
        )