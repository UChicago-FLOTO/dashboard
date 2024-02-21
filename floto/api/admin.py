import csv
import logging

from django import forms
from django.conf import settings
from django.contrib import admin
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import path

from floto.api.balena import get_balena_client
from floto.api.tasks import bulk_device_update_CSV
from floto.api.views import DeviceViewSet

from . import models

LOG = logging.getLogger(__name__)


class CollectionDeviceInline(admin.StackedInline):
    model = models.CollectionDevice

class CollectonAdmin(admin.ModelAdmin):
    inlines = (CollectionDeviceInline,)
    list_display = ["name", "created_by", "created_at", "created_by_project"]

admin.site.register(models.Collection, CollectonAdmin)


class ServicePeripheralInline(admin.StackedInline):
    model = models.ServicePeripheral

class ServiceAdmin(admin.ModelAdmin):
    list_display = ["container_ref", "created_by", "created_at", "created_by_project"]
    inlines = (
        ServicePeripheralInline,
    )

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
    description="Move devices to application (k8s) fleet"
)
def move_device_to_application_fleet(modeladmin, request, queryset):
    balena = get_balena_client()
    target_fleet = models.Fleet.objects.get(is_app_fleet=True)
    for obj in queryset.all():
        LOG.info(f"Moving {obj.device_uuid} to fleet {target_fleet.app_name}")
        balena.models.device.move(obj.device_uuid, target_fleet.id)


class CsvImportForm(forms.Form):
    csv_file = forms.FileField()

class DeviceDataAdmin(admin.ModelAdmin):
    form = DeviceDataForm
    # overrides the change_list.html template to show import and download csv links
    change_list_template = "admin/devices_change_list_admin.html"
    list_display = ["name", "device_uuid", "owner_project", "fleet", "created_at", "address"]
    list_filter = ["fleet", "name", "device_uuid"]
    actions = [move_device_to_application_fleet]

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('import-device-update-csv/', self.import_device_update_CSV),
            path('download-device-details/', self.download_device_details),
        ]
        return my_urls + urls

    def download_device_details(self, request):
        response = HttpResponse(
            content_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="device_details.csv"'},
        )
        writer = csv.writer(response)
        device_update_columns = [
            "device_uuid",
            "name",
            "deployment_name",
            "contact",
            "address_1",
            "address_2",
            "city",
            "state",
            "country",
            "zip_code",
            "latitude",
            "longitude",
        ]
        writer.writerow(device_update_columns)
        devices = models.DeviceData.objects.all()
        for device in devices:
            device_row = [getattr(device, attr, '') for attr in device_update_columns]
            writer.writerow(device_row)
        return response

    def import_device_update_CSV(self, request):
        if request.method == "POST":
            csv_file = request.FILES["csv_file"]
            decoded_file = csv_file.read().decode('utf-8').splitlines()
            # trigger a celery task to process the CSV
            bulk_device_update_CSV.delay(decoded_file)
            self.message_user(request, "Your csv file is importing", "info")
            return redirect("..")
        form = CsvImportForm()
        payload = {"form": form}
        return render(
            request, "admin/csv_form.html", payload
        )


admin.site.register(models.DeviceData, DeviceDataAdmin)


class PeripheralSchemaResourceInline(admin.TabularInline):
    model = models.PeripheralSchemaResource


class PeripheralSchemaConfigItemInline(admin.TabularInline):
    model = models.PeripheralSchemaConfigItem


class PeripheralSchemaAdmin(admin.ModelAdmin):
    list_display = ["type"]
    inlines = (
        PeripheralSchemaResourceInline,
        PeripheralSchemaConfigItemInline,
    )


admin.site.register(models.PeripheralSchema, PeripheralSchemaAdmin)


class PeripheralAdmin(admin.ModelAdmin):
    pass


admin.site.register(models.Peripheral, PeripheralAdmin)


class PeripheralConfigItemInline(admin.TabularInline):
    model = models.PeripheralConfigurationItem


class PeripheralInstanceAdmin(admin.ModelAdmin):
    inlines = (
        PeripheralConfigItemInline,
    )


admin.site.register(models.PeripheralInstance, PeripheralInstanceAdmin)
