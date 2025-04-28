from django.contrib import admin
from .models import KeycloakUser

import logging

LOG = logging.getLogger(__name__)


class CustomUserAdmin(admin.ModelAdmin):
    readonly_fields = [
        "has_project",
        "password",
        "id",
        "groups",
        "last_login",
        "date_joined",
        "user_permissions",
    ]
    list_display = ("email", "has_project", "is_staff", "is_superuser")

    @admin.display(description="Has a project")
    def has_project(self, instance):
        return any(instance.projects.all())


admin.site.register(KeycloakUser, CustomUserAdmin)
