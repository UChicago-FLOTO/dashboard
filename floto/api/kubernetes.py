import logging
from kubernetes import client, config

LOG = logging.getLogger(__name__)


def get_devices():
    config.load_kube_config(config_file="/config/kube/config")
    core_api = client.CoreV1Api()
    return core_api.list_node(
        label_selector="node-role.kubernetes.io/floto-worker=true")


def create_deployment(devices, job):
    config.load_kube_config(config_file="/config/kube/config")

    for device in devices:
        node_uuid = device["device_uuid"].replace("-", "")
        containers = []
        for app_service in job.application.services.all():
            service = app_service.service
            containers.append(
                client.V1Container(
                    image=service.container_ref,
                    name=f"name-{job.application.uuid}",
                    image_pull_policy="IfNotPresent",
                )
            )

        # TODO apply env to pod
        pod_name = f"app-{str(node_uuid)[:6]}-{str(job.application.uuid)[:6]}"
        v1_job = client.V1Job(
            api_version="batch/v1",
            kind="Job",
            metadata=client.V1ObjectMeta(
                name=f"job-{job.uuid}", labels={"job_name": f"job-{job.uuid}"}
            ),
            spec=client.V1JobSpec(
                backoff_limit=0,
                template=client.V1PodTemplateSpec(
                    spec=client.V1PodSpec(
                        restart_policy="Never",
                        containers=containers,
                        node_name=node_uuid,
                    ),
                    metadata=client.V1ObjectMeta(
                        name=pod_name,
                        labels={"pod_name": pod_name}
                    ),
                )
            ),
        )
        namespace = f"job-{job.uuid}"

        core_api = client.CoreV1Api()
        core_api.create_namespace(
            client.V1Namespace(metadata=client.V1ObjectMeta(name=namespace))
        )
        batch_api = client.BatchV1Api()
        batch_api.create_namespaced_job(namespace, v1_job)
