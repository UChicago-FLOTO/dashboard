from django.contrib import messages
from django.http import HttpResponse
from django.http import JsonResponse
from django.template import loader
from django.urls import reverse

import collections
import datetime
import requests
import balena
import json

def get_releases_by_id(request):
    releases_by_id = {}
    for release in get_all_releases(request):
        releases_by_id[release["id"]] = release
    return releases_by_id

def get_fleets_by_id(request):
    fleet_res = requests.get(
        request.build_absolute_uri(reverse('api:applications'))).json()
    fleets_by_id = {}
    for fleet in fleet_res["applications"]:
        fleets_by_id[fleet["id"]] = fleet
    return fleets_by_id

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

def devices(request):
    url = request.build_absolute_uri(reverse('api:devices'))
    res = requests.get(url).json()
    collapsable_device_fields = [
        "api_heartbeat_state",
        "is_online",
        "status",
        "provisioning_state",
        "os_version",
        "supervisor_version",
        "running_release",
        "fleet",
    ]
    identifiable_fields = [
        "uuid",
        "device_name",
        "ip_address",
        "mac_address",
        "last_vpn_event",
        "last_connectivity_event",
    ]
    merged_devices = collections.defaultdict(list)

    releases_by_id = get_releases_by_id(request)
    fleets_by_id = get_fleets_by_id(request)

    for device in res["devices"]:
        filtered_device = transform_device_dict(releases_by_id, fleets_by_id, device)
        filtered_device = {
            k: v for k, v in device.items() if k in collapsable_device_fields
        }
        filtered_device_tuple = tuple([
            (k, v) for k, v in filtered_device.items()
        ])
        merged_devices[filtered_device_tuple].append({
            k: v for k, v in device.items() if k in identifiable_fields
        })

    row_data = []
    for shared_data, devices in merged_devices.items():
        row_data.append({
            c[0]: c[1] for c in shared_data
        })
        row_data[-1]["devices"] = devices

    row_data = sorted(row_data, key=lambda r: len(r["devices"]), reverse=True)

    template = loader.get_template("dashboard/devices.html")
    context = {
        "devices": res["devices"],
        "row_data": row_data,
    }
    return HttpResponse(template.render(context, request))



def get_all_releases(request, fleet=None):
    releases = []
    if not fleet:
        url = request.build_absolute_uri(reverse('api:applications'))
        res = requests.get(url).json()
        fleets = [f["id"] for f in res["applications"]]
    else:
        fleets = [fleet]
    fleets_by_id = get_fleets_by_id(request)
    for fleet in fleets:
        url = request.build_absolute_uri(reverse('api:releases', args=[fleet]))
        res = requests.get(url).json()
        for r in res["releases"]:
            releases.append({
                "id": r["id"],
                "created_at": r["created_at"],
                "commit": r["commit"],
                "note": r["note"] if r["note"] else "",
            })
            releases[-1]["fleet"] = \
                    fleets_by_id[r["belongs_to__application"]["__id"]]
    return releases

def device(request, uuid):
    url = request.build_absolute_uri(reverse('api:device', args=[uuid]))
    res = requests.get(url).json()

    releases_by_id = get_releases_by_id(request)
    fleets_by_id = get_fleets_by_id(request)

    device = res["device"]
    transform_device_dict(releases_by_id, fleets_by_id, device)
    context = {
        "device": device,
    }
    template = loader.get_template("dashboard/device.html")
    return HttpResponse(template.render(context, request))


def releases(request, fleet=None):
    releases = get_all_releases(request, fleet)

    context = {
       "releases": sorted(releases, key=lambda r: (r["id"]), reverse=True),
    }
    template = loader.get_template("dashboard/releases.html")
    return HttpResponse(template.render(context, request))

def fleets(request):
    url = request.build_absolute_uri(reverse('api:applications'))
    res = requests.get(url).json()
    releases_by_id = get_releases_by_id(request)
    processed_fleets = []
    for fleet in res["applications"]:
        processed_fleets.append({
            "app_name": fleet["app_name"],
        })
        try:
            release_id = fleet["should_be_running__release"]["__id"]
            note = releases_by_id[release_id]["note"]
            processed_fleets[-1]["target_release"] = note if note else release_id
        except (KeyError, TypeError):
            processed_fleets[-1]["target_release"] = "None"

    context = {
        "fleets": processed_fleets,
    }
    template = loader.get_template("dashboard/fleets.html")
    return HttpResponse(template.render(context, request))

def logs(request, uuid, count=100):
    url = request.build_absolute_uri(reverse('api:logs', args=[uuid, count]))
    res = requests.get(url).json()
    processed_logs = []
    for entry in res["logs"]:
        processed_logs.append({
            "message": entry["message"],
            "timestamp": datetime.datetime.fromtimestamp(entry["timestamp"]/1000).strftime("%m/%d/%Y %H:%M:%S")
        })
    template = loader.get_template("dashboard/logs.html")
    context = {
        "uuid": uuid,
        "logs": processed_logs,
        "count": count,
    }
    return HttpResponse(template.render(context, request))

def overview(request):
    context = {}
    template = loader.get_template("dashboard/overview.html")
    return HttpResponse(template.render(context, request))
