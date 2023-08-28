from django.http import HttpResponse
from django.template import loader

import datetime

from . import util


def devices(request):
    template = loader.get_template("dashboard/devices.html")
    context = {}
    return HttpResponse(template.render(context, request))


def device(request, uuid):
    context = {
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
    fleets = util.get(request, "fleet-list", [])
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
    args = {"pk": uuid, "count": count}
    logs = util.get(request, "device-logs", request_kwargs=args, default_ret=[])
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
        "api_key": request.user.auth_token.key,
    }
    template = loader.get_template("dashboard/user.html")
    return HttpResponse(template.render(context, request))
