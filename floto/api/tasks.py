from celery.app import shared_task
from floto.api.balena import get_balena_client
from floto.api.kubernetes import get_nodes, label_node, get_namespaces_with_no_pods, delete_namespace_if_exists
from floto.api.models import DeviceData, Fleet, Project

from django.conf import settings

import logging
import os
import csv

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


@shared_task(name="sync_balena_device_to_db")
def sync_balena_device_to_db():
    """
    Syncs balena data to local database

    1. Stores fleets from balena
    2. Updates devices with that fleet information
    """
    balena = get_balena_client()
    for fleet in balena.models.application.get_all():
        obj, created = Fleet.objects.get_or_create(
            app_name=fleet["app_name"],
            id=fleet["id"],
        )
        if created:
            LOG.info(f"Created fleet object '${obj.app_name}'")
    devices = balena.models.device.get_all()
    for device in devices:
        try:
            obj = DeviceData.objects.get(device_uuid=device["uuid"])
            obj.fleet = Fleet.objects.get(pk=device["belongs_to__application"]["__id"])
            obj.save()
        except DeviceData.DoesNotExist:
            obj = DeviceData(
                device_uuid=device["uuid"],
                name=device["device_name"],
                allow_all_projects=False,
                owner_project=Project.objects.get(pk=settings.FLOTO_ADMIN_PROJECT),
                fleet=Fleet.objects.get(pk=device["belongs_to__application"]["__id"]),
            )
            obj.save()
            if created:
                LOG.info(f"New device '${obj.name}'")


@shared_task(name="rename_devices")
def rename_devices():
    """
    Renames devices based on UUID
    """
    label_filepath = "/config/device_labels.csv"
    if os.path.isfile(label_filepath):
        labels = {}
        with open(label_filepath) as f:
            labelreader=csv.DictReader(f)
            for l in labelreader:
                uuid = l.get("uuid")
                name = l.get("labelname")
                labels[uuid]=name
        balena = get_balena_client()
        for d in balena.models.device.get_all():
            device_name = d.get("device_name")
            device_uuid = d.get("uuid")
            labelname = labels.get(device_uuid)
            if labelname and labelname != device_name:
                LOG.info(f"setting device name from {device_name} to {labelname}")
                balena.models.device.rename(device_uuid,labelname)
