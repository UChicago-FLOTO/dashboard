from django.contrib.auth.decorators import login_required
from django.urls import path

from . import views

urlpatterns = [
    path(
        "",
        login_required(views.overview),
        name="overview"),
    path(
        "devices",
        login_required(views.devices),
        name="devices"),
    path(
        "devices/<str:uuid>/",
        login_required(views.device),
        name="device"),
    path(
        "devices/<str:uuid>/logs/",
        login_required(views.logs),
        name="logs"),
    path(
        "devices/<str:uuid>/logs/<int:count>/",
        login_required(views.logs),
        name="logs"),
    path(
        "releases/",
        login_required(views.releases),
        name="releases"),
    path(
        "releases/<int:fleet>/",
        login_required(views.releases),
        name="releases"),
    path(
        "fleets",
        login_required(views.fleets),
        name="fleets"),
    path("user", login_required(views.user), name="user"),
    path("services", login_required(views.services), name="services"), ]
