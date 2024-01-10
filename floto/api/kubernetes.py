from collections import defaultdict
import logging
import json
from kubernetes import client, config
from django.conf import settings
import hashlib

from . import util
from .balena import get_balena_client

LOG = logging.getLogger(__name__)


def get_namespace_name(job_uuid):
    return f"job-{job_uuid}"

def get_job_name(job_uuid, device_uuid):
    # We need different job names per device, and need length < 64.
    # hexdigest 6 gives a hash of length 12, which means out job name
    # will be 4 (prefix) + 36 (uuid) + 12 (hash) = 52.
    uuid_hash = hashlib.shake_256(
        get_node_uuid(device_uuid).encode()).hexdigest(6)
    return f"job-{job_uuid}-{uuid_hash}"

def get_node_uuid(device_uuid):
    return device_uuid.replace("-", "")

def get_pod_name(app_uuid, device_uuid):
    return f"app-{get_node_uuid(device_uuid)[:6]}-{str(app_uuid)[:6]}"


def get_volume_name():
    return "floto-volume"


def get_nodes():
    config.load_kube_config(config_file=settings.KUBE_CONFIG_FILE)
    core_api = client.CoreV1Api()
    return core_api.list_node(
        label_selector="node-role.kubernetes.io/floto-worker=true")


def get_namespaces_with_no_pods():
    config.load_kube_config(config_file=settings.KUBE_CONFIG_FILE)
    core_api = client.CoreV1Api()
    namespaces = [
        ns for ns in core_api.list_namespace().items
        if ns.metadata.name.startswith("job-")
        and core_api.list_namespaced_pod(ns.metadata.name).items.length == 0
    ]
    return namespaces


def get_job_events(uuid):
    config.load_kube_config(config_file=settings.KUBE_CONFIG_FILE)
    core_api = client.CoreV1Api()
    event_list = core_api.list_namespaced_event(get_namespace_name(uuid))
    events = [
        {
            "message": e.message,
            "created_at": e.first_timestamp,
            "updated_at": e.last_timestamp,
            "type": e.type,
        }
        for e in event_list.items
    ]
    sorted(events, key=lambda e: e["created_at"])
    return events


def delete_job_namespace_if_exists(job_obj):
    core_api = client.CoreV1Api()
    try:
        core_api.delete_namespace(get_namespace_name(job_obj.uuid))
    except client.exceptions.ApiException as e:
        # Ignore not found, meaning namespace was already deleted
        if e.status != 404:
            raise e

def destroy_job(job_obj):
    config.load_kube_config(config_file=settings.KUBE_CONFIG_FILE)
    batch_api = client.BatchV1Api()
    for device in job_obj.devices.all():
        try:
            batch_api.delete_namespaced_job(
                get_namespace_name(job_obj.uuid), 
                get_job_name(job_obj.uuid, device.device_uuid)
            )
        except client.exceptions.ApiException as e:
            # Ignore not found, meaning pod was deleted by k8s
            if e.status != 404:
                raise e
    delete_job_namespace_if_exists(job_obj)


def get_job_logs(uuid):
    """
    Returns a map of 
    {
        device: {
            container: logs
        }
    }
    """
    config.load_kube_config(config_file=settings.KUBE_CONFIG_FILE)
    core_api = client.CoreV1Api()
    logs = defaultdict(dict)
    pod_list = core_api.list_namespaced_pod(get_namespace_name(uuid))
    for pod in pod_list.items:
        for container in pod.spec.containers:
            try:
                logs[pod.spec.node_name][container.image] = core_api.read_namespaced_pod_log(
                    pod.metadata.name, get_namespace_name(uuid), container=container.name)
            except :
                # Device probably went down
                logs[pod.spec.node_name][container.image] = "Error getting logs for this container."
    return logs


def create_deployment(devices, job):
    config.load_kube_config(config_file=settings.KUBE_CONFIG_FILE)

    environment = json.loads(job.environment).items()
    balena = get_balena_client()

    namespace = get_namespace_name(job.uuid)
    core_api = client.CoreV1Api()
    core_api.create_namespace(
        client.V1Namespace(
            metadata=client.V1ObjectMeta(name=namespace),
            spec=client.V1NamespaceSpec(
                finalizers=[]
            )
        )
    )

    # Copy image pull secrets to newly created namespace
    for secret_name in settings.KUBE_IMAGE_PULL_SECRETS:
        secret = core_api.read_namespaced_secret(
            secret_name, settings.KUBE_SECRET_NAMESPACE)
        core_api.create_namespaced_secret(namespace, client.V1Secret(
            data=secret.data,
            type="kubernetes.io/dockerconfigjson",
            metadata=client.V1ObjectMeta(
                namespace=namespace,
                name=secret_name,
            ),
        ))

    for device in devices:
        containers = []

        device_environment = {
            "FLOTO_JOB_UUID": str(job.uuid),
            "FLOTO_DEVICE_UUID": device["device_uuid"],
        }
        device_environment.update({
            env_obj["name"]: env_obj["value"]
            for env_obj in 
            balena.models.device.env_var.get_all_by_device(uuid_or_id=device["device_uuid"])
            if env_obj["name"].startswith(settings.FLOTO_ENV_PREFIX)
        })
        # Overwrite any variables with the job's env
        device_environment.update(environment)

        volume_name = get_volume_name()
        pod_name = get_pod_name(job.application.uuid, device["device_uuid"])

        for app_service in job.application.services.all():
            service = app_service.service
            containers.append(
                client.V1Container(
                    image=service.container_ref,
                    name=f"container-{service.uuid}",
                    image_pull_policy="IfNotPresent",
                    env=[
                        client.V1EnvVar(name=n, value=v)
                        for n, v in device_environment.items()
                    ],
                    volume_mounts=[
                        client.V1VolumeMount(
                            mount_path=settings.KUBE_VOLUME_MOUNT_PATH,
                            name=volume_name
                        )
                    ]
                )
            )

        v1_job = client.V1Job(
            api_version="batch/v1",
            kind="Job",
            metadata=client.V1ObjectMeta(
                name=get_job_name(job.uuid, device["device_uuid"]),
                labels={"job_name": get_job_name(job.uuid, device["device_uuid"])},
            ),
            spec=client.V1JobSpec(
                backoff_limit=0,
                ttl_seconds_after_finished=settings.KUBE_JOB_TTL,
                template=client.V1PodTemplateSpec(
                    spec=client.V1PodSpec(
                        restart_policy="Never",
                        containers=containers,
                        node_name=get_node_uuid(device["device_uuid"]),
                        volumes=[
                            client.V1Volume(
                                name=volume_name,
                                empty_dir=client.V1EmptyDirVolumeSource(
                                    size_limit=settings.KUBE_VOLUME_SIZE
                                )
                            )
                        ],
                        image_pull_secrets=[
                            client.V1LocalObjectReference(
                                name=secret_name
                            )
                            for secret_name in 
                            settings.KUBE_IMAGE_PULL_SECRETS
                        ],
                        dns_policy="None",
                        dns_config=client.V1PodDNSConfig(
                            nameservers=["8.8.8.8"],
                        )
                    ),
                    metadata=client.V1ObjectMeta(
                        name=pod_name,
                        labels={"pod_name": pod_name}
                    ),
                )
            ),
        )
        for job_timing in job.timings.all():
            string_parts = job_timing.timing.split(",")
            timing_type, args = string_parts[0], string_parts[1:]
            if timing_type == "type=on_demand":
                td = util.parse_on_demand_args(args)
                v1_job.spec.active_deadline_seconds = int(td.total_seconds())

        batch_api = client.BatchV1Api()
        batch_api.create_namespaced_job(namespace, v1_job)
