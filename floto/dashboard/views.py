from django.http import HttpResponse
from django.template import loader

import datetime
import logging
import json

from . import util
from . import forms

LOG = logging.getLogger(__name__)


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


def logs(request, uuid, count=100):
    args = {"pk": uuid, "count": count}
    logs = util.getURL(request, "api:device-logs", request_kwargs=args, default_ret=[])
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


def services(request):
    if request.method == "POST":
        form = forms.ServiceForm(request.POST)
        if form.is_valid():
            util.post(request, "api:service-list", body=form.cleaned_data)

    services = util.getURL(request, "api:service-list", [])

    context = {
        "services": services,
        "form": forms.ServiceForm(),
    }
    template = loader.get_template("dashboard/services.html")
    return HttpResponse(template.render(context, request))


def applications(request):
    form = None
    services = util.getURL(request, "api:service-list", [])
    if request.method == "POST":
        form = forms.ApplicationForm(request.POST, services=services)
        if form.is_valid():
            body = {
                "name": form.cleaned_data["name"],
                "is_public": form.cleaned_data["is_public"],
                "description": form.cleaned_data["description"],
                "environment": json.dumps(form.cleaned_data["environment"]),
            }
            body["services"] = [
                {"service": s} for s in form.cleaned_data["services"]
            ]
            util.post(request, "api:application-list", body=body)

    applications = util.getURL(request, "api:application-list", [])
    for app in applications:
        app_services = [
            s for s in services
            if any(s["uuid"] == str(d["service"]) for d in app["services"])
        ]
        app["services"] = app_services
    LOG.info(applications)
    context = {
        "applications": applications,
        "form": form or forms.ApplicationForm(services=services),
    }
    template = loader.get_template("dashboard/applications.html")
    return HttpResponse(template.render(context, request))


def jobs(request):
    jobs = util.getURL(request, "api:job-list", [])
    applications = util.getURL(request, "api:application-list", [])
    devices = [
        d for d in util.getURL(request, "api:device-list", [])
        if d["belongs_to__application"]["__id"] == 13
    ]

    form = None
    if request.method == "POST":
        form = forms.JobForm(request.POST, applications=applications, devices=devices)
        if form.is_valid():
            body = {
                "is_public": form.cleaned_data["is_public"],
                "environment": json.dumps(form.cleaned_data["environment"]),
                "devices": [
                    {"device_uuid": d} for d in form.cleaned_data["devices"]
                ],
                "timings": [
                    {"timing": t} for t in form.cleaned_data["timings"].split("\n")
                ],
                "application": form.cleaned_data["application"]
            }
            util.post(request, "api:job-list", body=body)


    active_jobs = []
    inactive_jobs = []
    for job in jobs:
        job["application"] = next(a for a in applications if a["uuid"] == job["application"])
        job["environment"] = json.loads(job["environment"])
        now = datetime.datetime.now()
        if len(job["timeslots"]) == 0:
            job["state"] = "Not scheduled"
        elif all(now < util.parse_date(t["start"]) for t in job["timeslots"]):
            # All slots have yet to run
            job["state"] = "Pending"
        elif all(util.parse_date(t["stop"]) < now for t in job["timeslots"]):
            # All slots have finished
            job["state"] = "Completed"
        else:
            # Else, mid way through execution
            job["state"] = "Active"

        for timeslot in job["timeslots"]:
            timeslot["device_name"] = next(
                d for d in devices if timeslot["device_uuid"] == d["uuid"]
            ).get("device_name")

        if job["state"] in ["Active", "Pending"]:
            active_jobs.append(job)
        else:
            inactive_jobs.append(job)

    context = {
        "active_jobs": active_jobs,
        "inactive_jobs": inactive_jobs,
        "form": form or forms.JobForm(
            devices=devices,
            applications=applications,
        ),
    }
    template = loader.get_template("dashboard/jobs.html")
    return HttpResponse(template.render(context, request))
