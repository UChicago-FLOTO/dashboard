import secrets
from functools import cached_property

import django.contrib.auth.models as auth_models
from django import dispatch
from django.db import models, transaction
from django.db.models import signals
from keycloak import KeycloakError
from rest_framework.authtoken import models as token_models

from floto.auth.keycloak import KeycloakClient


def new_api_token():
    key_length = token_models.Token._meta.get_field("key").max_length
    n_secret_bytes = int(key_length * (3 / 4) - 2)
    return secrets.token_urlsafe(nbytes=n_secret_bytes)


class KeycloakUserManager(auth_models.UserManager):
    """
    Overrides the default Django UserManager to strip out fields that should be managed by Keycloak
    """

    def create_user(self, username, email=None, password=None, **extra_fields):
        try:
            keycloak_client = KeycloakClient()
            keycloak_user = keycloak_client.get_user_by_username(email)
        except KeycloakError as e:
            raise ValueError(f"Failed to fetch user {email} from Keycloak") from e
        return super().create_user(
            username, email, password=None, id=keycloak_user.get("id"), **extra_fields
        )


class KeycloakUser(auth_models.AbstractUser):
    """
    Represents a Django user mapped to a Keycloak user
    """

    # Aligned with the UUID in Keycloak, allowing FLOTO to link internal data to a Keycloak user
    id = models.UUIDField(primary_key=True)

    PASSWORD_ERROR_MESSAGE = "Keycloak users should not have passwords set via FLOTO"

    objects = KeycloakUserManager()

    @cached_property
    def keycloak_username(self):
        """
        This refers to the username stored in Keycloak, rather than this model's USERNAME_FIELD,
        which just points to the ID
        """
        return self.keycloak_user.get("username")

    @cached_property
    def is_active(self):
        return self.keycloak_user.get("enabled", False)

    def get_full_name(self):
        first_name = self.keycloak_user.get("firstName", "")
        last_name = self.keycloak_user.get("lastName" "")
        return f"{first_name} {last_name}".strip()

    def get_short_name(self):
        return self.keycloak_user.get("firstName")

    def set_password(self, _):
        raise NotImplementedError(self.PASSWORD_ERROR_MESSAGE)

    def check_password(self, _):
        raise NotImplementedError(self.PASSWORD_ERROR_MESSAGE)

    @property
    def keycloak_client(self):
        return KeycloakClient()

    @cached_property
    def keycloak_user(self):
        return self.keycloak_client.get_user_by_id(self.id)

    @transaction.atomic
    def rotate_api_token(self):
        # The key can't be updated because it is the model's primary key.
        # Therefore, the whole model has to be replaced
        self.auth_token.delete()
        return token_models.Token.objects.create(user=self, key=new_api_token())


@dispatch.receiver(signals.post_save, sender=KeycloakUser)
def generate_token(sender, instance, created, **kwargs):
    """
    When a user model needs a token, automatically generate one
    """
    if not token_models.Token.objects.filter(user=instance).exists():
        token_models.Token.objects.create(user=instance, key=new_api_token())
