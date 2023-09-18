from django.contrib import admin
from . import models

class CollectionDeviceInline(admin.StackedInline):
    model = models.CollectionDevice

class CollectonAdmin(admin.ModelAdmin):
    inlines = (CollectionDeviceInline,)

# admin.site.register(models.Collection, CollectonAdmin)

class ServiceAdmin(admin.ModelAdmin):
    list_display = ["container_ref", "created_by", "created_at"]

admin.site.register(models.Service, ServiceAdmin)


class ApplicationServiceInline(admin.StackedInline):
    model = models.ApplicationService

class ApplicationAdmin(admin.ModelAdmin):
    list_display = ["name", "created_by", "created_at"]
    inlines = (ApplicationServiceInline,)

admin.site.register(models.Application, ApplicationAdmin)


class JobAdmin(admin.ModelAdmin):
    pass

admin.site.register(models.Job, JobAdmin)