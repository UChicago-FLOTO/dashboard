from email.policy import default
import requests
import logging
from django.urls import reverse
from django.contrib import messages
from floto.api.views import FleetViewSet, DeviceViewSet

LOG = logging.getLogger(__name__)

VIEWS = {
    "device-list": DeviceViewSet.as_view({"get": "list"}),
    "device-detail": DeviceViewSet.as_view({"get": "retrieve"}),
    "device-logs": DeviceViewSet.as_view({"get": "logs"}),
    "fleet-list": FleetViewSet.as_view({"get": "list"}),
    "fleet-releases": FleetViewSet.as_view({"get": "releases"}),
}

def get(request, view_name, request_kwargs=None, default_ret=None):
    if not request_kwargs:
        request_kwargs = {}
    res = VIEWS.get(view_name)(request, **request_kwargs)
    if res.status_code == 200:
        return res.data
    else:
        try:
            data = res.data
            messages.error(request, data["detail"])
        except Exception:
            messages.error(request, "Unexpected error")
    return default_ret


def get_releases_by_id(request):
    """Get a dictionary of (id, release_json)"""
    releases_by_id = {}
    for release in get_all_releases(request):
        releases_by_id[release["id"]] = release
    return releases_by_id


def get_fleets_by_id(request):
    """Get a dictionary of (id, fleet_json)"""
    fleets = get(request, "fleet-list", [])
    fleets_by_id = {}
    for fleet in fleets:
        fleets_by_id[fleet["id"]] = fleet
    return fleets_by_id


def get_all_releases(request, fleet=None):
    """Get all releases, across all fleets"""
    releases = []
    if not fleet:
        applications = get(request, "fleet-list", [])
        fleets = [f["id"] for f in applications]
    else:
        fleets = [fleet]
    fleets_by_id = get_fleets_by_id(request)
    for fleet in fleets:
        res = get(request, "fleet-releases", request_kwargs={"pk": fleet}, default_ret=[])
        for r in res:
            r["fleet"] = fleets_by_id[r["belongs_to__application"]["__id"]]
            r["note"] = r["note"] if r["note"] else ""
            releases.append(r)
    return releases


def transform_device_dict(releases_by_id, fleets_by_id, device):
    try:
        release_id = device["is_running__release"]["__id"]
        note = releases_by_id[release_id]["note"]
        device["running_release"] = note if note else release_id
    except (KeyError, TypeError):
        device["running_release"] = "None"
    try:
        fleet_id = device["belongs_to__application"]["__id"]
        device["fleet"] = fleets_by_id[fleet_id]["app_name"]
    except (KeyError, TypeError):
        device["fleet"] = "None"
