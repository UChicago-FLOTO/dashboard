from mozilla_django_oidc.auth import OIDCAuthenticationBackend

class FlotoAuthBackend(OIDCAuthenticationBackend):
    def get_or_create_user(self, access_token, id_token, payload):
        user = super().get_or_create_user(access_token, id_token, payload)
        return user
