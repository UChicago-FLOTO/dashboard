from django.conf import settings

import balena
import logging
LOG = logging.getLogger(__name__)

global _balena_client
_balena_client = None


def _login():
    global _balena_client
    _balena_client = balena.Balena()
    _balena_client.auth.settings.set(
        "api_endpoint", settings.BALENA_API_ENDPOINT)
    _balena_client.auth.settings.set(
        "pine_endpoint", settings.BALENA_PINE_ENDPOINT)
    credentials = {
        'username': settings.BALENA_USERNAME,
        'password': settings.BALENA_PASSWORD
    }
    _balena_client.auth.login(**credentials)


def get_balena_client():
    global _balena_client
    if not _balena_client:
        _login()
    else:
        try:
            # Check API connectivity
            _balena_client.auth.who_am_i()
        except Exception:
            _login()
    return _balena_client


def with_balena():
    def decorator(func):
        def wrapper(request, *args, **kwargs):
            _balena_client = get_balena_client()
            return func(_balena_client, request, *args, **kwargs)
        return wrapper
    return decorator
