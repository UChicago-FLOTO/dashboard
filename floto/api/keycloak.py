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

    def get_user_id(self, username):
        return self.keycloak_admin.get_user_id(username)

    def get_user(self, username):
        user_id = self.get_user_id(username)
        user = self.keycloak_admin.get_user(user_id)
        LOG.info(user)
        return user

    def get_user_groups(self, username):
        user_id = self.get_user_id(username)
        groups = self.keycloak_admin.get_user_groups(
            user_id, brief_representation=False)
        return groups
