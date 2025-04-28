import logging

from rest_framework import permissions
from rest_framework.permissions import SAFE_METHODS
from floto.api.models import DeviceData
from floto.api.serializers import DeviceSerializer

LOG = logging.getLogger(__name__)


class MethodAllowed(permissions.BasePermission):
    def has_permission(self, request, view):
        # User has permission if any of the following apply
        # 1. they are requesting GET
        # 2. they are authenticated with a project
        if request.method in ["GET"]:
            return True
        if not request.user.is_authenticated:
            return False
        return any(request.user.projects.all())

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class IsOwnerOfObject(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.created_by == request.user


class DevicePermission(permissions.BasePermission):
    MANAGEMENT_VIEWS = {
        "device": {
            "Logs": True,
            "Environment retrieve": True,
            "Command": True,
            "Device action": True,
            "Device peripherals": True,
            "Device peripheral delete": True,
        }
    }

    APPLICATION_VIEWS = {}

    def has_permission(self, request, view):
        # Always check for management permission
        if DevicePermission.MANAGEMENT_VIEWS.get(view.basename, {}).get(view.name):
            pk = view.kwargs.get("pk")
            if pk:
                device = DeviceData.objects.get(pk=pk)
                return DeviceSerializer(
                    device,
                    context={
                        "balena_device": {},
                        "kubernetes_node": {},
                        "request": request,
                    },
                ).data["management_access"]
        # Check write methods against application views
        if (
            request.method not in SAFE_METHODS
            and DevicePermission.APPLICATION_VIEWS.get(view.basename, {}).get(view.name)
        ):
            pk = view.kwargs.get("pk")
            if pk:
                device = DeviceData.objects.get(pk=pk)
                return DeviceSerializer(
                    device,
                    context={
                        "balena_device": {},
                        "kubernetes_node": {},
                        "request": request,
                    },
                ).data["application_access"]
        # Otherwise, view is allowed
        return True
