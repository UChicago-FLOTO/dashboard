from rest_framework import permissions


class IsAdmin(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        # TODO check if the user has scipe
        return True
