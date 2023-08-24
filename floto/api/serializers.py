from rest_framework import serializers

from floto.api.models import Collection, CollectionDevice


class CollectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Collection
        fields = "__all__"


class CollectionDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = CollectionDevice
        fields = "__all__"
