from django.contrib import admin
from django.conf import settings
from django import forms
from floto.api.balena import get_balena_client

from floto.api.views import DeviceViewSet
from . import models

import logging

LOG = logging.getLogger(__name__)


class CollectionDeviceInline(admin.StackedInline):
    model = models.CollectionDevice

class CollectonAdmin(admin.ModelAdmin):
    inlines = (CollectionDeviceInline,)
    list_display = ["name", "created_by", "created_at", "created_by_project"]

admin.site.register(models.Collection, CollectonAdmin)

class ServiceAdmin(admin.ModelAdmin):
    list_display = ["container_ref", "created_by", "created_at", "created_by_project"]

admin.site.register(models.Service, ServiceAdmin)


class ApplicationServiceInline(admin.StackedInline):
    model = models.ApplicationService


class ApplicationAdmin(admin.ModelAdmin):
    list_display = ["name", "created_by", "created_at", "created_by_project"]
    inlines = (ApplicationServiceInline,)


admin.site.register(models.Application, ApplicationAdmin)


class JobTimeslotInline(admin.StackedInline):
    model = models.JobTiming

    def has_add_permission(self, request, obj=None):
        return False


class JobDeviceInline(admin.StackedInline):
    model = models.JobDevice

    def has_add_permission(self, request, obj=None):
        return False


class DeviceTimeslotInline(admin.StackedInline):
    model = models.DeviceTimeslot

    def has_add_permission(self, request, obj=None):
        return False


class JobAdmin(admin.ModelAdmin):
    list_display = ["uuid", "created_by", "created_at", "created_by_project"]
    inlines = (
        JobDeviceInline, JobTimeslotInline, DeviceTimeslotInline,)


admin.site.register(models.Job, JobAdmin)


class ProjectAdmin(admin.ModelAdmin):
    list_display = ["created_at", "uuid", "name"]

admin.site.register(models.Project, ProjectAdmin)


class DeviceDataForm(forms.ModelForm):
    device_uuid = forms.ChoiceField(required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        balena = get_balena_client()
        devices = balena.models.device.get_all()
        self.fields["device_uuid"].choices = [
            (d["uuid"], f"{d['device_name']} ({d['uuid']})")
            for d in devices
        ]

    class Meta:
        model = models.DeviceData
        fields = "__all__"


@admin.action(
    description="Create models for missing device data (doesn't use selected)."
)
def init_default_device_data(modeladmin, request, queryset):
    balena = get_balena_client()
    devices = balena.models.device.get_all()
    for device in devices:
        models.DeviceData(
            device_uuid=device["uuid"],
            name=device["device_name"],
            allow_all_projects=False,
            owner_project=models.Project.objects.get(pk=settings.FLOTO_ADMIN_PROJECT),
        ).save()

class DeviceDataAdmin(admin.ModelAdmin):
    form = DeviceDataForm
    list_display = ["name", "device_uuid", "owner_project"] 
    actions = [init_default_device_data]

admin.site.register(models.DeviceData, DeviceDataAdmin)
