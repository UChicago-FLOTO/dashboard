from django.urls import path

from . import views

urlpatterns = [
    path("devices", views.devices, name="devices"),
    path("devices/<str:uuid>/", views.device, name="device"),
    path("logs/<str:uuid>/<int:count>/", views.logs, name="logs"),
    path("releases/<int:fleet>", views.releases, name="releases"),
    path("applications", views.applications, name="applications"),
    path("note", views.note, name="note"),
    path("command", views.command, name="command"),
]
