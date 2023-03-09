from django.conf import settings
from django.http import JsonResponse

import base64
import ssl
import socket
import paramiko

from .balena import get_balena_client
from balena import exceptions

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response


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

    @action(methods=["POST"], detail=True, url_path="command/")
    def command(self, request, pk):
        balena = get_balena_client()
        jwt = balena.auth.settings.get("token")
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
                    "/keys/id_rsa")  # TODO
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
