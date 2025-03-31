import csv
from datetime import datetime, timezone
import logging
import os
import time


from celery.app import shared_task
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from floto.api import kubernetes

from floto.api.balena import get_balena_client
from floto.api.kubernetes import (get_nodes, label_node)
from floto.api.models import DeviceData, Fleet, Job, Project, Event

LOG = logging.getLogger(__name__)


@shared_task(name='label_nodes')
def label_nodes():
    """
    Label all kubernetes nodes that match to balena devices
    """
    nodes = get_nodes(label_selector="!node-role.kubernetes.io/floto-worker")
    for node in nodes:
        try:
            LOG.info(f"Giving floto-worker role to name {node.metadata.name}")
            label_node(node.metadata.name)
        except:
            # Node is unknown, do not do anything
            pass


@shared_task(name='cleanup_namespaces')
def cleanup_namespaces():
    """
    Cleanup all jobs that are over in k8s
    """
    for job in Job.objects_all.filter(cleaned_up=False):
        # If all timeslots have finished, we can terminate in k8s
        ts = job.timeslots.filter(stop__gte=datetime.now(timezone.utc))
        if not ts:
            LOG.info(f"Cleaning up job {job.uuid}")
            kubernetes.destroy_job(job)

            job.cleaned_up = True
            job.save()


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
            labelreader = csv.DictReader(f)
            for label in labelreader:
                uuid = label.get("uuid")
                name = label.get("labelname")
                labels[uuid] = name
        balena = get_balena_client()
        for d in balena.models.device.get_all():
            device_name = d.get("device_name")
            device_uuid = d.get("uuid")
            labelname = labels.get(device_uuid)
            if labelname and labelname != device_name:
                LOG.info(f"setting device name from {device_name} to {labelname}")
                balena.models.device.rename(device_uuid, labelname)


@shared_task(name="bulk_device_update_csv_reader")
def bulk_device_update_csv_reader(devices_data):
    """Updates devices' metadata from param:devices_data

    Args:
        devices_data (list): list of dicts with keys as device attributes
    """
    for row in devices_data:
        try:
            device = DeviceData.objects.get(device_uuid=row["device_uuid"])
        except ObjectDoesNotExist:
            LOG.error(f"device with UUID - {row['device_uuid']} does not exist. Skipping")
            continue
        device.device_uuid = row["device_uuid"]
        device.deployment_name = row["deployment_name"]
        device.contact = row["contact"]
        device.address_1 = row["address_1"]
        device.address_2 = row["address_2"]
        device.city = row["city"]
        device.state = row["state"]
        device.country = row["country"]
        device.zip_code = row["zip_code"]
        if row["latitude"] and row["longitude"]:
            device.latitude = float(row["latitude"])
            device.longitude = float(row["longitude"])
        try:
            device.save()
        except Exception as e:
            LOG.error(f"Error while updating device with UUID - {row['device_uuid']} from CSV - {e}")
        # sleep to honor the rate limit for geocode API
        time.sleep(1)


@shared_task(name='deploy_jobs')
def deploy_jobs():
    """
    Deploy all pending jobs that have reached their time
    """
    for event in Event.objects.filter(
        status="PENDING",
        time__lt=datetime.now(),
    ):
        with transaction.atomic():
            job = event.timing.job
            device_uuids = [
                ts.device_uuid for ts in job.timeslots.all()
            ]
            LOG.info(f"Exec {job.uuid} with {len(device_uuids)} devices")
            try:
                if not settings.KUBE_READ_ONLY:
                    kubernetes.create_deployment(device_uuids, job)
                event.status = "DONE"
                event.save()
            except Exception as e:
                LOG.error(f"Error deploy job {job.uuid}:")
                LOG.error(e)
                event.status = "ERROR"
                event.save()
