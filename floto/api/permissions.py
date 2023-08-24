import logging

from rest_framework import permissions

from floto.auth.keycloak import KeycloakClient

LOG = logging.getLogger(__name__)


class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        username = request.user.email

        kc = KeycloakClient()

        groups = request.session.get("groups", None)
        if not groups:
            groups = kc.get_user_groups(username)
            request.session["groups"] = groups
        return any([g["name"] == "admin" for g in groups])

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)
