from django.conf import settings

import balena
import logging
LOG = logging.getLogger(__name__)


def get_balena_client():
    balena_client = balena.Balena()
    balena_client.settings.set(
        "api_endpoint", settings.BALENA_API_ENDPOINT)
    balena_client.settings.set(
        "pine_endpoint", settings.BALENA_PINE_ENDPOINT)
    credentials = {
        'username': settings.BALENA_USERNAME,
        'password': settings.BALENA_PASSWORD
    }
    balena_client.auth.login(**credentials)
    return balena_client


def with_balena():
    def decorator(func):
        def wrapper(request, *args, **kwargs):
            balena_client = get_balena_client()
            return func(balena_client, request, *args, **kwargs)
        return wrapper
    return decorator
