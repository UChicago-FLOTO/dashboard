from keycloak import KeycloakAdmin


from django.conf import settings

import logging

LOG = logging.getLogger(__name__)


class KeycloakClient:
    def __init__(self):
        self.keycloak_admin = KeycloakAdmin(
            server_url="https://auth.floto.science",
            client_id=settings.OIDC_RP_ADMIN_CLIENT_ID,
            client_secret_key=settings.OIDC_RP_ADMIN_CLIENT_SECRET,
            realm_name="floto",
            user_realm_name="floto",
        )

    def get_user_by_email(self, email):
        users = self.keycloak_admin.get_users({"email": email})
        if len(users) != 1:
            LOG.error(f"Error getting user by email {email}. Expected 1, got:")
            LOG.error(users)
        return users[0]

    def get_user_by_id(self, user_id):
        user = self.keycloak_admin.get_user(user_id)
        return user

    def get_user_groups(self, email):
        user_id = self.get_user_by_email(email)["id"]
        groups = self.keycloak_admin.get_user_groups(
            user_id, brief_representation=False
        )
        return groups

    def add_user_to_group(self, email, group):
        user_id = self.get_user_by_email(email)["id"]
        groups = self.keycloak_admin.get_groups({"name": group})
        if len(groups) != 1:
            LOG.error(f"Error getting group by name {group}. Expected 1, got:")
            LOG.error(groups)
        group_id = groups[0]["id"]
        self.keycloak_admin.group_user_add(user_id, group_id)
