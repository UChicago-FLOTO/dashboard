from django.contrib import admin
from .models import KeycloakUser
from .keycloak import KeycloakClient

import logging

LOG = logging.getLogger(__name__)


@admin.action(description="Approve account")
def approve_account(modeladmin, request, queryset):
    for user in queryset.all():
        kc = KeycloakClient()
        kc.add_user_to_group(user.email, "admin")

class CustomUserAdmin(admin.ModelAdmin):
    actions = [approve_account]
    readonly_fields = [
        "is_approved",
        "password",
        "id",
        "groups",
        "last_login",
        "date_joined",
        "user_permissions",
    ]
    list_display = ("email", "is_approved", "is_staff", "is_superuser")

    @admin.display(description="Approved to use FLOTO")
    def is_approved(self, instance):
        kc = KeycloakClient()
        return any(g for g in kc.get_user_groups(instance.email) 
                if g["name"] == "admin")


admin.site.register(KeycloakUser, CustomUserAdmin)
