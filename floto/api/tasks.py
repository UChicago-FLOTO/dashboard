from celery.app import shared_task
from floto.api.kubernetes import get_namespaces_with_no_pods
from floto.api.models import Job

import logging

LOG = logging.getLogger(__name__)

@shared_task(name='cleanup_namespaces')
def cleanup_namespaces():
    # TODO make this actually clean things up eventually.
    # (We need a dev space for it first)
    LOG.info(get_namespaces_with_no_pods())
