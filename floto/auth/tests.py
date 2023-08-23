from django.test import TestCase
from django.urls import reverse
from rest_framework import status

from floto.auth.models import KeycloakUser


class ApiKeyTest(TestCase):
    """
    Tests that valid API Keys can be used to authenticate
    """

    test_user = None

    def setUp(self) -> None:
        self.test_user = KeycloakUser.objects.create_user("test", "test@test.com", "")

    def test_api_key_authentication(self):
        test_key = self.test_user.auth_token.key
        test_url = reverse("api:fleet-list")

        response = self.client.get(
            test_url, headers={"Authorization": f"Token {test_key}"}
        )
        self.assertEquals(response.status_code, status.HTTP_200_OK)

    def test_bad_api_key_authentication(self):
        test_key = self.test_user.auth_token.key
        test_url = reverse("api:fleet-list")
        replace_char = test_key[0]
        new_char = chr((ord(replace_char) + 1) % 256)
        test_key = test_key.replace(replace_char, new_char)

        response = self.client.get(
            test_url, headers={"Authorization": f"Token {test_key}"}
        )
        self.assertEquals(response.status_code, status.HTTP_401_UNAUTHORIZED)
