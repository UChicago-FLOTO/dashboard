from django.db import models
from rest_framework import serializers
from django.contrib.auth.models import User
import uuid
from datetime import datetime


class Collection(models.Model):
    user = models.CharField(max_length=300)
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4)
    name = models.CharField(max_length=200)
    description = models.CharField(max_length=2000)
    is_public = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=datetime.now, blank=True)
    created_by = models.CharField(max_length=200)


class CollectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Collection
        fields = '__all__'


class CollectionDevice(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    collection_uuid = models.UUIDField(primary_key=True, default=uuid.uuid4(), editable=False)
    device_uuid = models.UUIDField


class CollectionDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = CollectionDevice
        fields = '__all__'
