import csv
import logging

from django import forms
from django.conf import settings
from django.contrib import admin
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import path

from floto.api.balena import get_balena_client
from floto.api.tasks import bulk_device_update_csv_reader
from floto.api.views import DeviceViewSet

from . import models

LOG = logging.getLogger(__name__)


class CollectionDeviceInline(admin.StackedInline):
    model = models.CollectionDevice

class CollectionAdmin(admin.ModelAdmin):
    inlines = (CollectionDeviceInline,)
    list_display = ["name", "created_by", "created_at", "created_by_project"]

admin.site.register(models.Collection, CollectionAdmin)


class ServicePeripheralInline(admin.StackedInline):
    model = models.ServicePeripheral

class ServiceClaimableResourceInline(admin.StackedInline):
    model = models.ServiceClaimableResource

class ServiceAdmin(admin.ModelAdmin):
    list_display = ["container_ref", "created_by", "created_at", "created_by_project"]
    inlines = (
        ServicePeripheralInline, ServiceClaimableResourceInline,
    )

admin.site.register(models.Service, ServiceAdmin)


class ClaimableResourceAdmin(admin.ModelAdmin):
    list_display = ["resource"]

admin.site.register(models.ClaimableResource, ClaimableResourceAdmin)

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


@admin.action(
    description="Retire devices"
)
def retire_devices(modeladmin, request, queryset):
    with transaction.atomic():
        for obj in queryset.all():
            obj.status = 'retired'
            obj.save()


class GeocodeListFilter(admin.SimpleListFilter):
    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options.
    title = _("Is Geocoded")

    # Parameter for the filter that will be used in the URL query.
    parameter_name = "is_geocoded"

    def lookups(self, request, model_admin):
        """
        Returns a list of tuples. The first element in each
        tuple is the coded value for the option that will
        appear in the URL query. The second element is the
        human-readable name for the option that will appear
        in the right sidebar.
        """
        return [
            ("yes", _("Yes")),
            ("no", _("No")),
        ]

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.
        """
        # Compare the requested value (either '80s' or '90s')
        # to decide how to filter the queryset.
        if self.value() == "yes":
            return queryset.filter(
                latitude__isnull=False,
                longitude__isnull=False,
            )
        if self.value() == "no":
            return queryset.filter(
                latitude__isnull=True,
                longitude__isnull=True,
            )


class CsvImportForm(forms.Form):
    csv_file = forms.FileField()


class DeviceDataAdmin(admin.ModelAdmin):
    form = DeviceDataForm
    # overrides the change_list.html template to show import and download csv links
    change_list_template = "admin/devices_change_list_admin.html"
    list_display = ["name", "device_uuid", "owner_project", "fleet", "created_at", "address", "contact"]
    list_filter = [GeocodeListFilter, "fleet", "name"]
    actions = [move_device_to_application_fleet, retire_devices]

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
        writer.writerow(models.DeviceData.device_update_columns)
        devices = models.DeviceData.objects.all()
        for device in devices:
            device_row = [getattr(device, attr, '') for attr in models.DeviceData.device_update_columns]
            writer.writerow(device_row)
        return response

    def import_device_update_CSV(self, request):
        if request.method == "POST":
            csv_file = request.FILES["csv_file"]
            try:
                if not csv_file:
                    self.message_user(
                        request, "CSV file is required.", "error"
                    )
                    raise Exception
                try:
                    decoded_file = csv_file.read().decode('utf-8').splitlines()
                    reader = csv.DictReader(decoded_file)
                except Exception as e:
                    self.message_user(
                        request, "Error with CSV file", "error"
                    )
                    raise e
                try:
                    reader = csv.DictReader(decoded_file)
                except csv.Error as e:
                    self.message_user(
                        request, f"Error with CSV file updated: {e}", "error"
                    )
                    raise e
                missing_columns = [
                    col
                    for col in models.DeviceData.device_update_columns
                    if col not in reader.fieldnames
                ]
                if missing_columns:
                    self.message_user(
                        request,
                        f"Missing columns in CSV: {', '.join(missing_columns)}",
                        "error"
                    )
                    raise ValueError
            except Exception:
                # if exceptions, return to form page and show error message
                pass
            else:
                devices_data = [row for row in reader]
                # trigger a celery task to process the CSV
                bulk_device_update_csv_reader.delay(devices_data)
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
