import logging

from rest_framework import permissions

LOG = logging.getLogger(__name__)


class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        groups = request.session.get("groups", [])
        return any([g["name"] == "admin" for g in groups])

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class IsOwnerOfObject(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.created_by == request.user
