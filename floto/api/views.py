from django.conf import settings
from django.http import HttpResponse
from django.http import JsonResponse

import json
import base64
import ssl
import socket
import paramiko

from .balena import with_balena
from balena import exceptions


@with_balena()
def devices(balena, request):
    res = balena.models.device.get_all()
    return JsonResponse({"devices": res})


@with_balena()
def device(balena, request, uuid):
    res = balena.models.device.get(uuid)
    return JsonResponse({"device": res})


@with_balena()
def logs(balena, request, uuid, count):
    res = balena.logs.history(uuid, count)
    return JsonResponse({"logs": res})


@with_balena()
def releases(balena, request, fleet):
    try:
        res = balena.models.release.get_all_by_application(fleet)
        return JsonResponse({"releases": res})
    except exceptions.ReleaseNotFound:
        return JsonResponse({"releases": []})


@with_balena()
def applications(balena, request):
    res = balena.models.application.get_all()
    return JsonResponse({"applications": res})


@with_balena()
def note(balena, request):
    res = balena.models.release.set_note(
        request.POST["id"], request.POST["note"])
    return JsonResponse({"status": "OK"})


@with_balena()
def command(balena, request):
    jwt = balena.auth.settings.get("token")
    device_uuid = request.POST["uuid"]
    command = request.POST["command"]
    ssh_port = settings.BALENA_TUNNEL_PORT
    encoded_auth = base64.b64encode(
        f'admin:{jwt}'.encode("utf-8")).decode("utf-8")
    headers = [
        f"CONNECT {device_uuid}.balena:{ssh_port} HTTP/1.0",
        f"Proxy-Authorization: Basic {encoded_auth}",
    ]
    context = ssl.create_default_context()
    hostname = settings.BALENA_TUNNEL_HOST
    res = {}
    with socket.create_connection((hostname, 443)) as sock:
        with context.wrap_socket(sock, server_hostname=hostname) as ssock:
            ssock.sendall(("\r\n".join(headers) + '\r\n\r\n').encode("utf-8"))
            # Need to read http res before passing to SSH client
            ssock.recv(1024)  # TODO check this is 200 OK

            ssh_client = paramiko.client.SSHClient()
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            pkey = paramiko.RSAKey.from_private_key_file(
                "/keys/id_rsa")  # TODO
            ssh_client.connect("", username="root", pkey=pkey, sock=ssock)
            _, stdout, stderr = ssh_client.exec_command(command, get_pty=True)

            stdout_str = ""
            for line in iter(stdout.readline, ""):
                stdout_str += line
            res["stdout"] = stderr_str

            stderr_str = ""
            for line in iter(stderr.readline, ""):
                stderr_str += line
            res["stderr"] = stderr_str
    return JsonResponse(res)
