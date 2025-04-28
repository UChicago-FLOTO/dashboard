from collections import defaultdict
import logging
import json
from kubernetes import client, config
from django.conf import settings
import hashlib

from floto.api import models

from . import util
from .balena import get_balena_client

LOG = logging.getLogger(__name__)


def get_namespace_name(job_uuid):
    return f"job-{job_uuid}"


def get_job_name(job_uuid, device_uuid):
    # We need different job names per device, and need length < 64.
    # hexdigest 6 gives a hash of length 12, which means out job name
    # will be 4 (prefix) + 36 (uuid) + 12 (hash) = 52.
    uuid_hash = hashlib.shake_256(get_node_uuid(device_uuid).encode()).hexdigest(6)
    return f"job-{job_uuid}-{uuid_hash}"


def get_config_map_name(device_uuid):
    return f"config-{device_uuid}"


def get_node_uuid(device_uuid):
    return device_uuid.replace("-", "")


def get_pod_name(app_uuid, device_uuid):
    return f"app-{get_node_uuid(device_uuid)[:6]}-{str(app_uuid)[:6]}"


def get_service_name(device_uuid, service_uuid):
    return f"service-{get_node_uuid(device_uuid)[:6]}-{str(service_uuid)[:6]}"


def get_volume_name():
    return "floto-volume"


def load_config_for_device(device_uuid):
    fleet_name = models.DeviceData.objects.get(pk=device_uuid).fleet.app_name
    config_file = settings.KUBE_CLUSTERS.get(fleet_name)
    if config_file:
        config.load_kube_config(config_file)
    else:
        raise ValueError(f"No kubeconfig file for {fleet_name}")


def get_nodes(label_selector="node-role.kubernetes.io/floto-worker=true"):
    nodes = []
    for fleet_name, config_file in settings.KUBE_CLUSTERS.items():
        config.load_kube_config(config_file=config_file)
        core_api = client.CoreV1Api()
        # We query this because node names may not be unique across clusters,
        # so that we should only get the node from the correct fleet.
        fleet_devices = set(
            d.device_uuid
            for d in models.DeviceData.objects.filter(fleet__app_name=fleet_name)
        )
        for node in core_api.list_node(label_selector=label_selector).items:
            if node.metadata.name in fleet_devices:
                nodes.append(node)
    return nodes


def label_node(node_name, label="node-role.kubernetes.io/floto-worker", value="true"):
    load_config_for_device(node_name)
    core_api = client.CoreV1Api()
    core_api.patch_node(
        node_name,
        {
            "metadata": {
                "labels": {
                    label: value,
                }
            }
        },
    )


def get_namespaces_with_no_pods():
    namespaces = set()
    for config_file in settings.KUBE_CLUSTERS.values():
        config.load_kube_config(config_file=config_file)
        core_api = client.CoreV1Api()
        namespaces.update(
            ns
            for ns in core_api.list_namespace().items
            if ns.metadata.name.startswith("job-")
            and len(core_api.list_namespaced_pod(ns.metadata.name).items) == 0
        )
    return namespaces


def get_job_events(uuid):
    events = []
    for config_file in settings.KUBE_CLUSTERS.values():
        config.load_kube_config(config_file=config_file)
        core_api = client.CoreV1Api()
        event_list = core_api.list_namespaced_event(get_namespace_name(uuid))
        events.extend(
            {
                "message": e.message,
                "created_at": e.first_timestamp,
                "updated_at": e.last_timestamp,
                "type": e.type,
            }
            for e in event_list.items
        )
    sorted(events, key=lambda e: e["created_at"])
    return events


def delete_namespace_if_exists(namespace_name):
    for config_file in settings.KUBE_CLUSTERS.values():
        config.load_kube_config(config_file=config_file)
        core_api = client.CoreV1Api()
        try:
            core_api.delete_namespace(namespace_name)
        except client.exceptions.ApiException as e:
            # Ignore not found, meaning namespace was already deleted
            if e.status != 404:
                raise e


def destroy_job(job_obj):
    for device in job_obj.devices.all():
        try:
            load_config_for_device(device.device_uuid)
            batch_api = client.BatchV1Api()
            core_api = client.CoreV1Api()
            batch_api.delete_namespaced_job(
                namespace=get_namespace_name(job_obj.uuid),
                name=get_job_name(job_obj.uuid, device.device_uuid),
            )
        except client.exceptions.ApiException as e:
            # Ignore not found, meaning pod was deleted by k8s
            if e.status != 404:
                raise e
        for app_service in job_obj.application.services.all():
            service = app_service.service
            try:
                core_api.delete_namespaced_service(
                    namespace=get_namespace_name(job_obj.uuid),
                    name=get_service_name(device.device_uuid, service.uuid),
                )
            except client.exceptions.ApiException as e:
                # Ignore not found, meaning pod was deleted by k8s
                if e.status != 404:
                    raise e

    delete_namespace_if_exists(get_namespace_name(job_obj.uuid))


def get_job_logs(uuid):
    """
    Returns a map of
    {
        device: {
            container: logs
        }
    }
    """
    logs = defaultdict(dict)
    for config_file in settings.KUBE_CLUSTERS.values():
        config.load_kube_config(config_file=config_file)
        core_api = client.CoreV1Api()
        pod_list = core_api.list_namespaced_pod(get_namespace_name(uuid))
        for pod in pod_list.items:
            for container in pod.spec.containers:
                try:
                    logs[pod.spec.node_name][container.image] = (
                        core_api.read_namespaced_pod_log(
                            pod.metadata.name,
                            get_namespace_name(uuid),
                            container=container.name,
                        )
                    )
                except:
                    # Device probably went down
                    logs[pod.spec.node_name][container.image] = (
                        "Error getting logs for this container."
                    )
    return logs


def prepare_deployment(job):
    namespace = get_namespace_name(job.uuid)
    for config_file in settings.KUBE_CLUSTERS.values():
        config.load_kube_config(config_file=config_file)
        core_api = client.CoreV1Api()
        core_api.create_namespace(
            client.V1Namespace(
                metadata=client.V1ObjectMeta(name=namespace),
                spec=client.V1NamespaceSpec(finalizers=[]),
            )
        )
        # Copy image pull secrets to newly created namespace
        for secret_name in settings.KUBE_IMAGE_PULL_SECRETS:
            secret = core_api.read_namespaced_secret(
                secret_name, settings.KUBE_SECRET_NAMESPACE
            )
            core_api.create_namespaced_secret(
                namespace,
                client.V1Secret(
                    data=secret.data,
                    type="kubernetes.io/dockerconfigjson",
                    metadata=client.V1ObjectMeta(
                        namespace=namespace,
                        name=secret_name,
                    ),
                ),
            )


def create_deployment(devices, job):
    """
    Args:
        devices: [str (device_uuids)]
        job: models.Job
    """
    if type(job.environment) is str:
        environment = json.loads(job.environment).items()
    else:
        environment = job.environment.items()
    balena = get_balena_client()
    namespace = get_namespace_name(job.uuid)
    for device_uuid in devices:
        _create_job_for_device(job, device_uuid, environment, balena, namespace)


def _port_name(service_port):
    """Must conform to https://www.rfc-editor.org/rfc/rfc6335.txt
    - alphanumeric (a-z, and 0-9) string
    - with a maximum length of 15 characters
    - with the '-' character allowed anywhere except the first or the last
        character or adjacent to another '-' character
    - it must contain at least a (a-z) character.
    """
    # This implementation should be fine, provided we limit protocol to TCP/UDP
    return f"{service_port.protocol.lower()}-{service_port.target_port}"


def _create_job_for_device(job, device_uuid, job_environment, balena, namespace):
    load_config_for_device(device_uuid)
    core_api = client.CoreV1Api()
    containers = []

    device_environment = {
        "FLOTO_JOB_UUID": str(job.uuid),
        "FLOTO_DEVICE_UUID": device_uuid,
    }
    device_environment.update(
        {
            env_obj["name"]: env_obj["value"]
            for env_obj in balena.models.device.env_var.get_all_by_device(
                uuid_or_id=device_uuid
            )
            if env_obj["name"].startswith(settings.FLOTO_ENV_PREFIX)
        }
    )
    # Overwrite any variables with the job's env
    device_environment.update(job_environment)

    volume_name = get_volume_name()
    device_volume_name = f"lv-{device_uuid}"
    pod_name = get_pod_name(job.application.uuid, device_uuid)

    config_data = {}
    config_name = get_config_map_name(device_uuid)
    device_model = models.DeviceData.objects.get(pk=device_uuid)
    for p in device_model.peripherals.all():
        for item in p.peripheral.schema.configuration_items.all():
            value = ""
            try:
                value = p.configuration.get(label=item).value
            except:
                # Device is not configured with this option for some reason
                pass
            config_data[item.label] = value
    core_api.create_namespaced_config_map(
        namespace,
        client.V1ConfigMap(
            data=config_data, metadata=client.V1ObjectMeta(name=config_name)
        ),
    )

    k8s_services = []
    for app_service in job.application.services.all():
        service = app_service.service

        resources = defaultdict(int)
        for ps in service.peripheral_schemas.all():
            for resource in ps.peripheral_schema.resources.all():
                resources[resource.label] += resource.count

        service_ports = list(service.ports.all())
        containers.append(
            client.V1Container(
                image=service.container_ref,
                name=f"container-{service.uuid}",
                image_pull_policy="Always",
                env=[
                    client.V1EnvVar(name=n, value=v)
                    for n, v in device_environment.items()
                ],
                volume_mounts=[
                    client.V1VolumeMount(
                        mount_path=settings.KUBE_VOLUME_MOUNT_PATH, name=volume_name
                    ),
                    client.V1VolumeMount(
                        mount_path=settings.KUBE_PERIPHERAL_VOLUME_MOUNT_PATH,
                        name="peripheral-config",
                    ),
                    client.V1VolumeMount(
                        mount_path=settings.KUBE_DEVICE_VOLUME_MOUNT_PATH,
                        name=device_volume_name,
                    ),
                ],
                resources=client.V1ResourceRequirements(
                    limits={k: str(v) for k, v in resources.items()},
                ),
                ports=[
                    # We should specify this so the service can identify the container
                    client.V1ContainerPort(
                        name=_port_name(p),
                        container_port=p.target_port,
                    )
                    for p in service.ports.all()
                ],
            )
        )

        if service_ports:
            k8s_services.append(
                client.V1Service(
                    metadata=client.V1ObjectMeta(
                        name=get_service_name(device_uuid, service.uuid),
                    ),
                    spec=client.V1ServiceSpec(
                        type="NodePort",
                        selector={
                            "pod_name": pod_name,
                        },
                        ports=[
                            client.V1ServicePort(
                                port=p.target_port,
                                name=f"sp-{_port_name(p)}",
                                target_port=_port_name(p),
                                node_port=p.node_port,
                                protocol=p.protocol,
                            )
                            for p in service_ports
                        ],
                    ),
                )
            )

    v1_job = client.V1Job(
        api_version="batch/v1",
        kind="Job",
        metadata=client.V1ObjectMeta(
            name=get_job_name(job.uuid, device_uuid),
            labels={"job_name": get_job_name(job.uuid, device_uuid)},
        ),
        spec=client.V1JobSpec(
            backoff_limit=0,
            ttl_seconds_after_finished=settings.KUBE_JOB_TTL,
            template=client.V1PodTemplateSpec(
                spec=client.V1PodSpec(
                    restart_policy="Never",
                    containers=containers,
                    node_name=get_node_uuid(device_uuid),
                    volumes=[
                        client.V1Volume(
                            name=volume_name,
                            empty_dir=client.V1EmptyDirVolumeSource(
                                size_limit=settings.KUBE_VOLUME_SIZE
                            ),
                        ),
                        client.V1Volume(
                            name="peripheral-config",
                            config_map=client.V1ConfigMapVolumeSource(
                                name=config_name,
                            ),
                        ),
                        client.V1Volume(
                            name=device_volume_name,
                            host_path=client.V1HostPathVolumeSource(
                                path="/mnt/data/shared_volume",
                                type="DirectoryOrCreate",
                            ),
                        ),
                    ],
                    image_pull_secrets=[
                        client.V1LocalObjectReference(name=secret_name)
                        for secret_name in settings.KUBE_IMAGE_PULL_SECRETS
                    ],
                    dns_policy="None",
                    dns_config=client.V1PodDNSConfig(
                        nameservers=["8.8.8.8"],
                    ),
                ),
                metadata=client.V1ObjectMeta(
                    name=pod_name, labels={"pod_name": pod_name}
                ),
            ),
        ),
    )
    for job_timing in job.timings.all():
        string_parts = job_timing.timing.split(",")
        timing_type, args = string_parts[0], string_parts[1:]
        if timing_type == "type=on_demand":
            td = util.parse_on_demand_args(args)
            v1_job.spec.active_deadline_seconds = int(td.total_seconds())
        elif timing_type == "type=advanced":
            ts = util.parse_advanced_timing_args(args)
            td = ts["end"] - ts["start"]
            v1_job.spec.active_deadline_seconds = int(td.total_seconds())

    batch_api = client.BatchV1Api()
    batch_api.create_namespaced_job(namespace, v1_job)

    for service in k8s_services:
        core_api.create_namespaced_service(namespace, service)
