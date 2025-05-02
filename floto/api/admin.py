import csv
import logging

import nested_admin

from django import forms
from django.contrib import admin
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import path

from floto.api.balena import get_balena_client
from floto.api.tasks import bulk_device_update_csv_reader

from . import models

LOG = logging.getLogger(__name__)


class SoftDeleteAdmin(nested_admin.NestedModelAdmin):
    def get_queryset(self, request):
        return self.model.objects_all.all()

    ordering = ("-created_at",)


class CollectionDeviceInline(nested_admin.NestedStackedInline):
    model = models.CollectionDevice


class CollectionAdmin(SoftDeleteAdmin):
    inlines = (CollectionDeviceInline,)
    list_display = [
        "deleted",
        "name",
        "created_by",
        "created_at",
        "created_by_project",
    ]
    list_filter = ["deleted"]


admin.site.register(models.Collection, CollectionAdmin)


class ServicePeripheralInline(nested_admin.NestedStackedInline):
    model = models.ServicePeripheral


class ServiceClaimableResourceInline(nested_admin.NestedStackedInline):
    model = models.ServiceClaimableResource


class ServicePortInline(nested_admin.NestedStackedInline):
    model = models.ServicePort


class ServiceAdmin(SoftDeleteAdmin):
    list_display = [
        "deleted",
        "container_ref",
        "created_by",
        "created_at",
        "created_by_project",
    ]
    list_filter = ["deleted"]
    inlines = (
        ServicePeripheralInline,
        ServiceClaimableResourceInline,
        ServicePortInline,
    )


admin.site.register(models.Service, ServiceAdmin)


class ClaimableResourceAdmin(admin.ModelAdmin):
    list_display = ["resource"]


admin.site.register(models.ClaimableResource, ClaimableResourceAdmin)


class ApplicationServiceInline(nested_admin.NestedStackedInline):
    model = models.ApplicationService


class ApplicationAdmin(SoftDeleteAdmin):
    list_display = ["deleted", "name", "created_by", "created_at", "created_by_project"]
    list_filter = ["deleted"]
    inlines = (ApplicationServiceInline,)


admin.site.register(models.Application, ApplicationAdmin)


class EventInline(nested_admin.NestedStackedInline):
    model = models.Event

    def has_add_permission(self, request, obj=None):
        return False


class JobTimeslotInline(nested_admin.NestedStackedInline):
    model = models.JobTiming

    def has_add_permission(self, request, obj=None):
        return False

    inlines = [EventInline]


class JobDeviceInline(nested_admin.NestedStackedInline):
    model = models.JobDevice

    def has_add_permission(self, request, obj=None):
        return False


class DeviceTimeslotInline(nested_admin.NestedStackedInline):
    model = models.DeviceTimeslot

    def has_add_permission(self, request, obj=None):
        return False


class JobDeviceFilter(admin.SimpleListFilter):
    title = _("Device")

    parameter_name = "job_device"

    def lookups(self, request, model_admin):
        return [(d.device_uuid, _(str(d))) for d in models.DeviceData.objects.all()]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(
                devices__device_uuid=self.value(),
            )


class JobForm(forms.ModelForm):
    class Meta:
        model = models.Job
        fields = "__all__"
        widgets = {
            "environment": forms.Textarea(attrs={"rows": 5, "cols": 40}),
        }


class JobAdmin(SoftDeleteAdmin):
    list_display = [
        "deleted",
        "uuid",
        "created_by",
        "created_at",
        "created_by_project",
        "cleaned_up",
    ]
    list_filter = [
        "deleted",
        "created_at",
        "created_by",
        "application",
        "cleaned_up",
        JobDeviceFilter,
    ]
    inlines = (JobDeviceInline, JobTimeslotInline, DeviceTimeslotInline)
    form = JobForm


admin.site.register(models.Job, JobAdmin)


class DeviceDataInline(admin.TabularInline):
    model = models.DeviceData.application_projects.through
    fields = ("devicedata",)  # This is the reverse link
    extra = 0
    verbose_name = "Application Devices"
    verbose_name_plural = "Application Devices"
    # can_delete = True

    def has_change_permission(self, request, obj=None):
        return False  # Optional: make this read-only

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("devicedata").order_by("devicedata__name")

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.name == "devicedata":
            kwargs["queryset"] = models.DeviceData.objects.order_by("name")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class ProjectAdmin(admin.ModelAdmin):
    list_filter = ["members"]
    list_display = ["created_at", "uuid", "name"]
    filter_horizontal = ("members",)
    inlines = [DeviceDataInline]


admin.site.register(models.Project, ProjectAdmin)


class DeviceDataForm(forms.ModelForm):
    device_uuid = forms.ChoiceField(required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        balena = get_balena_client()
        devices = balena.models.device.get_all()
        self.fields["device_uuid"].choices = [
            (d["uuid"], f"{d['device_name']} ({d['uuid']})") for d in devices
        ]

    class Meta:
        model = models.DeviceData
        fields = "__all__"


@admin.action(description="Move devices to application (k8s) fleet")
def move_device_to_application_fleet(modeladmin, request, queryset):
    balena = get_balena_client()
    target_fleet = models.Fleet.objects.get(is_app_fleet=True)
    for obj in queryset.all():
        LOG.info(f"Moving {obj.device_uuid} to fleet {target_fleet.app_name}")
        balena.models.device.move(obj.device_uuid, target_fleet.id)


@admin.action(description="Retire devices")
def retire_devices(modeladmin, request, queryset):
    with transaction.atomic():
        for obj in queryset.all():
            obj.status = "retired"
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
    list_display = [
        "name",
        "device_uuid",
        "owner_project",
        "fleet",
        "created_at",
        "address",
        "contact",
    ]
    list_filter = [
        GeocodeListFilter,
        "fleet",
        "owner_project",
        "created_at",
        "application_projects",
    ]
    search_fields = [
        "name",
        "device_uuid",
        "contact",
        "address_1",
        "address_2",
        "city",
        "state",
        "zip_code",
    ]
    actions = [move_device_to_application_fleet, retire_devices]
    filter_horizontal = ("application_projects",)

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path("import-device-update-csv/", self.import_device_update_CSV),
            path("download-device-details/", self.download_device_details),
        ]
        return my_urls + urls

    def download_device_details(self, request):
        response = HttpResponse(
            content_type="text/csv",
            headers={
                "Content-Disposition": 'attachment; filename="device_details.csv"'
            },
        )
        writer = csv.writer(response)
        writer.writerow(models.DeviceData.device_update_columns)
        devices = models.DeviceData.objects.all()
        for device in devices:
            device_row = [
                getattr(device, attr, "")
                for attr in models.DeviceData.device_update_columns
            ]
            writer.writerow(device_row)
        return response

    def import_device_update_CSV(self, request):
        if request.method == "POST":
            csv_file = request.FILES["csv_file"]
            try:
                if not csv_file:
                    self.message_user(request, "CSV file is required.", "error")
                    raise Exception
                try:
                    decoded_file = csv_file.read().decode("utf-8").splitlines()
                    reader = csv.DictReader(decoded_file)
                except Exception as e:
                    self.message_user(request, "Error with CSV file", "error")
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
                        "error",
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
        return render(request, "admin/csv_form.html", payload)


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
    inlines = (PeripheralConfigItemInline,)


admin.site.register(models.PeripheralInstance, PeripheralInstanceAdmin)


class DatasetAdmin(admin.ModelAdmin):
    list_display = ["name", "created_by", "approved"]


admin.site.register(models.Dataset, DatasetAdmin)


class DatasetDownloadEventAdmin(admin.ModelAdmin):
    list_display = ["downloaded_at", "downloaded_by", "dataset"]
    ordering = ("-downloaded_at",)


admin.site.register(models.DownloadEvent, DatasetDownloadEventAdmin)


@admin.register(models.KubernetesEvent)
class KubernetesEventAdmin(admin.ModelAdmin):
    list_display = ('namespace', 'event_type', 'reason', 'involved_object_name', 'event_time', 'count')
    search_fields = ('reason', 'message', 'involved_object_name')
