from django.http import HttpResponse
from django.template import loader
from django.urls import reverse

import collections
import datetime

from . import util


def devices(request):
    url = request.build_absolute_uri(reverse('api:device-list'))
    devices = util.get(request, url)
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

    releases_by_id = util.get_releases_by_id(request)
    fleets_by_id = util.get_fleets_by_id(request)

    for device in devices:
        filtered_device = util.transform_device_dict(
            releases_by_id, fleets_by_id, device)
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
        "devices": devices,
        "row_data": row_data,
    }
    return HttpResponse(template.render(context, request))


def device(request, uuid):
    url = request.build_absolute_uri(
        reverse('api:device-detail', args=[uuid]))
    device = util.get(request, url)

    releases_by_id = util.get_releases_by_id(request)
    fleets_by_id = util.get_fleets_by_id(request)

    util.transform_device_dict(releases_by_id, fleets_by_id, device)
    context = {
        "device": device,
    }
    template = loader.get_template("dashboard/device.html")
    return HttpResponse(template.render(context, request))


def releases(request, fleet=None):
    releases = util.get_all_releases(request, fleet)

    context = {
       "releases": sorted(releases, key=lambda r: (r["id"]), reverse=True),
    }
    template = loader.get_template("dashboard/releases.html")
    return HttpResponse(template.render(context, request))


def fleets(request):
    url = request.build_absolute_uri(reverse('api:fleet-list'))
    fleets = util.get(request, url)
    releases_by_id = util.get_releases_by_id(request)
    processed_fleets = []
    for fleet in fleets:
        processed_fleets.append({
            "app_name": fleet["app_name"],
        })
        try:
            release_id = fleet["should_be_running__release"]["__id"]
            note = releases_by_id[release_id]["note"]
            processed_fleets[-1]["target_release"] = note \
                if note else release_id
        except (KeyError, TypeError):
            processed_fleets[-1]["target_release"] = "None"

    context = {
        "fleets": processed_fleets,
    }
    template = loader.get_template("dashboard/fleets.html")
    return HttpResponse(template.render(context, request))


def logs(request, uuid, count=100):
    url = request.build_absolute_uri(reverse('api:device-logs', args=[uuid, count]))
    logs = util.get(request, url)
    #raise Exception(logs)
    processed_logs = []
    for entry in logs:
        processed_logs.append({
            "message": entry["message"],
            "timestamp": datetime.datetime.fromtimestamp(
                entry["timestamp"]/1000).strftime("%m/%d/%Y %H:%M:%S"),
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


def user(request):
    context = {
        "user": request.user,
        "groups": request.user.groups.all(),
        "claims": dir(request.user),
    }
    template = loader.get_template("dashboard/user.html")
    return HttpResponse(template.render(context, request))
