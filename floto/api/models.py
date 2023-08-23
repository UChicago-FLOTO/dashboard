import uuid
from datetime import datetime

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.models import User
from django.db import models


class Collection(models.Model):
    user = models.CharField(max_length=300)
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4)
    name = models.CharField(max_length=200)
    description = models.CharField(max_length=2000)
    is_public = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=datetime.now, blank=True)
    created_by = models.CharField(max_length=200)


class CollectionDevice(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    collection_uuid = models.UUIDField(
        primary_key=True, default=uuid.uuid4(), editable=False
    )
    device_uuid = models.UUIDField
