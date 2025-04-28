import logging

from django.db.models import Q
from rest_framework import filters
from floto.api import kubernetes

from floto.api.models import DeviceData, PeripheralSchema
from floto.api.serializers import DeviceSerializer

LOG = logging.getLogger(__name__)


class HasReadAccessFilterBackend(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        """
        Filters a queryset to objects are either:
        - public
        - owned by the current user
        """
        active_project = None
        active_project_pk = request.query_params.get("active_project")
        if active_project_pk:
            active_project = request.user.projects.filter(pk=active_project_pk).first()

        if request.user.is_anonymous:
            return queryset.filter(Q(is_public=True))
        elif active_project:
            return queryset.filter(
                Q(created_by_project=active_project) | Q(is_public=True)
            )
        else:
            return queryset.filter(
                Q(created_by_project__in=request.user.projects.all())
                | Q(is_public=True)
            )


class DeviceFilter(filters.BaseFilterBackend):
    def filter_queryset(self, request, devices, view):
        filtered_devices = []
        try:
            nodes = kubernetes.get_nodes()
        except Exception as e:
            LOG.error(e)
            nodes = []

        nodes_by_id = {node.metadata.name: node for node in nodes}

        active_project = None
        active_project_pk = request.query_params.get("active_project")
        if active_project_pk:
            active_project = request.user.projects.filter(pk=active_project_pk).first()

        for device in devices:
            try:
                device_data = DeviceData.objects.get(device_uuid=device["uuid"])
                node_data = nodes_by_id.get(device["uuid"])

                json = DeviceSerializer(
                    device_data,
                    context={
                        "balena_device": device,
                        "kubernetes_node": node_data,
                        "request": request,
                        "active_project": active_project,
                        "peripheral_schemas": PeripheralSchema.objects.all(),
                    },
                ).data

                filtered_devices.append(json)
            except DeviceData.DoesNotExist:
                LOG.warning(f"Device {device['uuid']} does not have extra data!")
        return filtered_devices
