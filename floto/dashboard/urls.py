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
    path("services", login_required(views.services), name="services"),
    path("applications",
         login_required(views.applications), name="applications"),
    path("jobs", login_required(views.jobs), name="jobs"),
    path(
        "jobs/<str:uuid>/",
        login_required(views.job),
        name="job"),
    path("set_active_project", login_required(views.set_active_project), name="set_active_project"),
]
