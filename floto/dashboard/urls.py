from django.urls import path

from . import views

urlpatterns = [
    path("", views.overview, name="overview"),

    path("devices", views.devices, name="devices"),
    path("devices/<str:uuid>/", views.device, name="device"),
    path("devices/<str:uuid>/logs/", views.logs, name="logs"),
    path("devices/<str:uuid>/logs/<int:count>/", views.logs, name="logs"),
    path("devices/<str:uuid>/command/", views.logs, name="logs"),

    path("releases/", views.releases, name="releases"),
    path("releases/<int:fleet>/", views.releases, name="releases"),

    path("fleets", views.fleets, name="fleets"),
]
