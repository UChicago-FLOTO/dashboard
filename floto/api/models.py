from django.db import models
from rest_framework import serializers
from django.contrib.auth.models import User


class Collection(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    uuid = models.UUIDField
    owner = models.CharField(max_length=200)
    name = models.CharField(max_length=200)
    description = models.CharField
    is_public = models.BooleanField
    created_at = models.DateTimeField
    created_by = models.DateTimeField


class CollectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Collection
        fields = ('uuid', 'owner', 'name', 'description', 'is_public', 'created_at', 'created_by')


class CollectionDevice(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    collection_uuid = models.UUIDField
    device_uuid = models.UUIDField
