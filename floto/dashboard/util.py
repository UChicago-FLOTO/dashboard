import datetime
import logging
import requests

from django.contrib import messages
from django.urls import reverse

LOG = logging.getLogger(__name__)


def post(request, view_name, body=None, default_ret=None):
    headers = {k: v for k, v in request.headers.items()}
    headers["Accept"] = "application/json"
    headers["Cookie"] = request.headers["Cookie"]
    headers["Content-Type"] = "application/json"
    res = requests.post(
        request.build_absolute_uri(reverse(view_name)),
        json=body,
        headers=headers,
    )
    try:
        res_json = res.json()
        if res.status_code < 400:
            return res_json
        else:
            messages.error(request, res_json.get("detail", res_json))
    except Exception as e:
        LOG.error(e)
        res_json = None
        messages.error(
            request,
            f"Unexpected error, API returned status {res.status_code}. {res.text}")
    return default_ret


def getURL(request, view_name, request_kwargs=None, default_ret=None):
    if not request_kwargs:
        request_kwargs = {}
    headers = {k: v for k, v in request.headers.items()}
    headers["Accept"] = "application/json"
    res = requests.get(
        request.build_absolute_uri(
            reverse(view_name, kwargs=request_kwargs)
        ),
        headers=headers,
    )
    try:
        res_json = res.json()
        if res.status_code < 400:
            return res_json
        else:
            messages.error(request, res_json.get("detail", res_json))
    except Exception:
        res_json = None
        messages.error(
            request,
            f"Unexpected error, API returned status {res.status_code}")
    return default_ret


def get_releases_by_id(request):
    """Get a dictionary of (id, release_json)"""
    releases_by_id = {}
    for release in get_all_releases(request):
        releases_by_id[release["id"]] = release
    return releases_by_id


def get_fleets_by_id(request):
    """Get a dictionary of (id, fleet_json)"""
    fleets = getURL(request, "api:fleet-list", [])
    fleets_by_id = {}
    for fleet in fleets:
        fleets_by_id[fleet["id"]] = fleet
    return fleets_by_id


def get_all_releases(request, fleet=None):
    """Get all releases, across all fleets"""
    releases = []
    if not fleet:
        applications = getURL(request, "api:fleet-list", [])
        fleets = [f["id"] for f in applications]
    else:
        fleets = [fleet]
    fleets_by_id = get_fleets_by_id(request)
    for fleet in fleets:
        res = getURL(request, "api:fleet-releases",
                     request_kwargs={"pk": fleet}, default_ret=[])
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

def parse_date(date_string):
    return datetime.datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%S.%fZ")
