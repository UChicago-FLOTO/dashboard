import requests
import logging
from django.urls import reverse
from django.contrib import messages

LOG = logging.getLogger(__name__)


def get(request, url, default_ret=None):
    res = requests.get(url, cookies={"sessionid": request.session.session_key})
    data = res.json()
    if res.ok:
        return data
    else:
        messages.error(request, data["detail"])
    return default_ret

def get_releases_by_id(request):
    """Get a dictionary of (id, release_json)"""
    releases_by_id = {}
    for release in get_all_releases(request):
        releases_by_id[release["id"]] = release
    return releases_by_id


def get_fleets_by_id(request):
    """Get a dictionary of (id, fleet_json)"""
    fleets = get(request,
        request.build_absolute_uri(reverse('api:fleet-list')), [])
    fleets_by_id = {}
    for fleet in fleets:
        fleets_by_id[fleet["id"]] = fleet
    return fleets_by_id


def get_all_releases(request, fleet=None):
    """Get all releases, across all fleets"""
    releases = []
    if not fleet:
        url = request.build_absolute_uri(reverse('api:fleet-list'))
        applications = get(request, url, [])
        LOG.info(applications)
        fleets = [f["id"] for f in applications]
    else:
        fleets = [fleet]
    fleets_by_id = get_fleets_by_id(request)
    for fleet in fleets:
        url = request.build_absolute_uri(reverse('api:fleet-releases', args=[fleet]))
        res = get(request, url, [])
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
