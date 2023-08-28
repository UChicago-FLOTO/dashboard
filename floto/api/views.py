import json

import django.core.serializers
from django.conf import settings
from django.core import serializers
import base64
import ssl
import socket
import paramiko

from .balena import get_balena_client
from balena import exceptions

from floto.api.models import Collection
from floto.api.serializers import CollectionSerializer
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status


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


class CollectionViewSet(viewsets.ModelViewSet):

    def list(self, request, *args, **kwargs):
        collections = Collection.objects.all()
        collections_json = django.core.serializers.serialize('python', collections)
        data = {
            'user': request.user.id,
            'collection': collections_json
        }
        return Response(data=data)

    def retrieve(self, request, *args, **kwargs):
        collection = Collection.objects.get(pk=self.kwargs.get('pk'))
        collection_json = CollectionSerializer(collection).data
        return Response(data=collection_json)

    def create(self, request, *args, **kwargs):
        data = json.loads(request.data)
        user = request.user
        if user is None:
            user_id = ""
        else:
            user_id = user.id
        new_collection = Collection(
            user=user_id,
            name=data['name'],
            description=data['description'],
            is_public=data['is_public'],
            created_by=data['name'],
        )
        data = serializers.serialize('python', [new_collection])

        # Save the instance to the database
        new_collection.save()
        return Response(status=status.HTTP_200_OK, data=data)

    def update(self, request, *args, **kwargs):
        collection_uuid = self.kwargs.get('pk')
        try:
            instance = Collection.objects.get(uuid=collection_uuid)
        except Collection.DoesNotExist:
            data = {
                'message': 'Instance not found with Collection UUID ' + collection_uuid
            }
            return Response(data=data, status=status.HTTP_404_NOT_FOUND)

        data = json.loads(request.data)
        is_public = data.get('is_public', instance.is_public)
        description = data.get('description', instance.description)
        name = data.get('name', instance.name)
        instance.is_public = is_public
        instance.description = description
        instance.name = name
        instance.save()
        return Response(status=204)

    def destroy(self, request, *args, **kwargs):
        collection_uuid = self.kwargs.get('pk')
        try:
            instance = Collection.objects.get(uuid=collection_uuid)
        except Collection.DoesNotExist:
            return Response({'message': f'Instance not found {collection_uuid}.'}, status=status.HTTP_404_NOT_FOUND)

        instance.delete()
        return Response({'message': 'Collection deleted'}, status=status.HTTP_200_OK)


class EnvViewSet(viewsets.ViewSet):
    def retrieve(self, request, pk):
        client = get_balena_client()
        env = client.models.device.env_var.get_all_by_device(uuid_or_id=pk)
        return Response(env, status=status.HTTP_200_OK)

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
