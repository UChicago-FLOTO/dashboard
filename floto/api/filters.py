import logging

from django.db.models import Q
from rest_framework import filters
from floto.api import kubernetes

from floto.api.models import DeviceData

LOG = logging.getLogger(__name__)


class HasReadAccessFilterBackend(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        """
        Filters a queryset to objects are either:
        - public
        - owned by the current user
        """
        return queryset.filter(
            Q(created_by=request.user) | Q(is_public=True)
        )

class DeviceFilter(filters.BaseFilterBackend):
    def filter_queryset(self, request, devices, view):
        filtered_devices = []
        nodes = kubernetes.get_nodes()
        nodes_by_id = {
            node.metadata.name: node
            for node in nodes.items
        }

        active_project = None
        active_project_pk = request.query_params.get('active_project')
        if active_project_pk:
            active_project = request.user.projects.filter(pk=active_project_pk).first()

        for device in devices:
            try:
                device_data = DeviceData.objects.get(
                    device_uuid=device["uuid"])
                node_data = nodes_by_id.get(device["uuid"])
                json = device_data.public_dict(device, node_data, request, active_project)
                
                if (
                    json["management_access"] or 
                    json["application_access"]
                ):
                    filtered_devices.append(json)
            except DeviceData.DoesNotExist:
                LOG.warning(f"Device {device['uuid']} does not have extra data!")
        return filtered_devices