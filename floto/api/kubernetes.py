import logging
import json
from kubernetes import client, config
from django.conf import settings
import hashlib

from . import util
from .balena import get_balena_client

LOG = logging.getLogger(__name__)


def get_devices():
    config.load_kube_config(config_file=settings.KUBE_CONFIG_FILE)
    core_api = client.CoreV1Api()
    return core_api.list_node(
        label_selector="node-role.kubernetes.io/floto-worker=true")


def create_deployment(devices, job):
    config.load_kube_config(config_file=settings.KUBE_CONFIG_FILE)

    environment = json.loads(job.environment).items()
    balena = get_balena_client()

    namespace = f"job-{job.uuid}"
    core_api = client.CoreV1Api()
    core_api.create_namespace(
        client.V1Namespace(metadata=client.V1ObjectMeta(name=namespace))
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
        node_uuid = device["device_uuid"].replace("-", "")
        # We need different job names per device, and need length < 64.
        # hexdigest 6 gives a hash of length 12, which means out job name
        # will be 4 (prefix) + 36 (uuid) + 12 (hash) = 52.
        uuid_hash = hashlib.shake_256(node_uuid.encode()).hexdigest(6)
        job_name = f"job-{job.uuid}-{uuid_hash}"

        containers = []

        device_environment = {
            env_obj["name"]: env_obj["value"]
            for env_obj in 
            balena.models.device.env_var.get_all_by_device(uuid_or_id=device["device_uuid"])
        }
        # Overwrite any variables with the job's env
        device_environment.update(environment)

        volume_name = "floto-volume"
        pod_name = f"app-{str(node_uuid)[:6]}-{str(job.application.uuid)[:6]}"

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
                name=job_name,
                labels={"job_name": job_name},
            ),
            spec=client.V1JobSpec(
                backoff_limit=0,
                template=client.V1PodTemplateSpec(
                    spec=client.V1PodSpec(
                        restart_policy="Never",
                        containers=containers,
                        node_name=node_uuid,
                        volumes=[
                            client.V1Volume(
                                name=volume_name,
                                empty_dir=client.V1EmptyDirVolumeSource(
                                    size_limit=settings.KUBE_VOLUME_SIZE
                                )
                            )
                        ]
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
