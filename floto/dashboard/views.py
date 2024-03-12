from django.conf import settings
from django.http import HttpResponse
from django.template import loader

import datetime
import json
import logging
from django.views.decorators.clickjacking import xframe_options_exempt

from . import util
from .. import util as floto_util

LOG = logging.getLogger(__name__)


def devices(request):
    context = {}
    template = loader.get_template("dashboard/devices.html")
    return HttpResponse(template.render(context, request))


def device(request, uuid):
    context = {}
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
    fleets = util.getURL(request, "api:fleet-list", [])
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


def overview(request):
    context = {}
    template = loader.get_template("dashboard/overview.html")
    return HttpResponse(template.render(context, request))


@xframe_options_exempt
def map(request):
    template = loader.get_template("dashboard/map.html")
    return HttpResponse(template.render({}, request))


def user(request):
    context = {
        "user": request.user,
        "api_key": request.user.auth_token.key,
    }
    template = loader.get_template("dashboard/user.html")
    return HttpResponse(template.render(context, request))


def services(request):
    context = {}
    template = loader.get_template("dashboard/services.html")
    return HttpResponse(template.render(context, request))


def applications(request):
    context = {}
    template = loader.get_template("dashboard/applications.html")
    return HttpResponse(template.render(context, request))


def jobs(request):
    context = {}
    template = loader.get_template("dashboard/jobs.html")
    return HttpResponse(template.render(context, request))


def job(request, uuid):
    context = {}
    template = loader.get_template("dashboard/job.html")
    return HttpResponse(template.render(context, request))


def set_active_project(request):
    if request.method == 'POST':
        project = json.loads(request.body)
        floto_util.set_active_project(request, project["uuid"])
        return HttpResponse(status=204)
    else:
        return HttpResponse(status=405)