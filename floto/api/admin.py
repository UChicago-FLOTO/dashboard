from django.contrib import admin
from . import models

class CollectionDeviceInline(admin.StackedInline):
    model = models.CollectionDevice

class CollectonAdmin(admin.ModelAdmin):
    inlines = (CollectionDeviceInline,)
    list_display = ["name", "created_by", "created_at"]

admin.site.register(models.Collection, CollectonAdmin)

class ServiceAdmin(admin.ModelAdmin):
    list_display = ["container_ref", "created_by", "created_at"]

admin.site.register(models.Service, ServiceAdmin)


class ApplicationServiceInline(admin.StackedInline):
    model = models.ApplicationService


class ApplicationAdmin(admin.ModelAdmin):
    list_display = ["name", "created_by", "created_at"]
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
    list_display = ["uuid", "created_by", "created_at"]
    inlines = (
        JobDeviceInline, JobTimeslotInline, DeviceTimeslotInline,)


admin.site.register(models.Job, JobAdmin)