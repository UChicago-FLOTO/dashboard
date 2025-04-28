from floto.auth.keycloak import KeycloakClient

import logging

LOG = logging.getLogger(__name__)


class UserTokenMiddleware(object):
    """
    Sets the user's API token as a cookie, as long as the user is authenticated.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.user.is_authenticated and not request.COOKIES.get("token"):
            response.set_cookie("token", request.user.auth_token.key)
        elif not request.user.is_authenticated and request.COOKIES.get("token"):
            response.delete_cookie("token")
        return response
