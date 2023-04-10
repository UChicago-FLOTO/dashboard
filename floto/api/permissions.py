from rest_framework import permissions

from floto.api.keycloak import KeycloakClient

import logging
LOG = logging.getLogger(__name__)


class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        username = request.user.email

        kc = KeycloakClient()
        groups = kc.get_user_groups(username)
        return any([g["name"] == "admin" for g in groups])

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)
