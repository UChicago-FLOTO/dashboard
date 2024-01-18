from celery.app import shared_task
from django.conf import settings
from floto.api.balena import get_balena_client
from floto.api.kubernetes import get_nodes, label_node, get_namespaces_with_no_pods, delete_namespace_if_exists
from floto.api.models import DeviceData, Job

import logging

LOG = logging.getLogger(__name__)

@shared_task(name='label_nodes')
def label_nodes():
    """
    Label all kubernetes nodes that match to balena devices
    """
    nodes = get_nodes(label_selector="!node-role.kubernetes.io/floto-worker")
    nodes_by_id = [
        node.metadata.name
        for node in nodes.items
    ]
    for node in nodes.items:
        try:
            DeviceData.objects.get(device_uuid=node.metadata.name)
            LOG.info(f"Giving floto-worker role to name {node.metadata.name}")
            label_node(node.metadata.name)
        except:
            # Node is unknown, do not do anything
            pass


@shared_task(name='cleanup_namespaces')
def cleanup_namespaces():
    """
    Cleanup all namespaces with no pods.
    """
    namespaces = get_namespaces_with_no_pods()
    for ns in namespaces:
        LOG.info(f"Deleting empty job namespace {ns.metadata.name}")
        delete_namespace_if_exists(ns.metadata.name)