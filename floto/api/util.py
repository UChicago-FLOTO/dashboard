from collections import defaultdict
from rest_framework.exceptions import ValidationError
from datetime import datetime, timedelta
import logging
from floto.api import models


LOG = logging.getLogger(__name__)


def parse_on_demand_args(args):
    duration = {"hours": 0, "days": 0, "minutes": 0}
    for arg in args:
        parts = arg.split("=")
        if len(parts) != 2:
            raise ValidationError(
                f"Expected duration of form 'unit=123' but got '{parts}'")
        if parts[0] not in duration:
            raise ValidationError(f"Unknown duration unit: '{parts[0]}'")
        try:
            duration[parts[0]] = int(parts[1])
        except ValueError as e:
            raise ValidationError(
                f"Invalid duration '{parts[1]}' in '{parts}'")
    return timedelta(**duration)

    

def parse_timing_string(value):
    """
    Parse the given timing string into a list of (start, end) tuples
    """
    string_parts = value.split(",")
    timing_type, args = string_parts[0], string_parts[1:]
    if timing_type == "type=on_demand":
        return [{
            "start": datetime.now(),
            "stop": datetime.now() + parse_on_demand_args(args),
        }]
    else:
        raise ValidationError(f"Invalid timing string {value}")


def parse_timings(timings, devices, application_uuid):
    """
    Parse the list of timings and devices into
    {
        "conflicts": [
            {"start": , "stop"}
        ],
        "timeslots": {
            timing string: [
                {"start": , "stop"}
            ]
        }
    }
    """
    db_app = models.Application.objects.get(pk=application_uuid)
    db_services = [s.service for s in db_app.services.all()]
    db_app_peripherals = set(
        p.peripheral_schema.type
        for s in db_services
        for p in s.peripheral_schemas.all()
    )
    db_app_resources = set(
        r.resource.resource
        for s in db_services
        for r in s.resources.all()
    )
    db_app_ports = set(
        p.node_port
        for s in db_services
        for p in s.ports.all()
    )

    res = {
        "conflicts": defaultdict(list),
        "timeslots": {},
    }
    # Generate timeslots
    for timing in timings:
        res["timeslots"][timing["timing"]] = parse_timing_string(timing["timing"])

    # Compute conflicts
    device_uuids = [d["device_uuid"] for d in devices]
    for timeslots in res["timeslots"].values():
        for timeslot in timeslots:
            start = timeslot["start"]
            end = timeslot["stop"]
            # Get all conflicting timeslots on this device. Timeslots collide if either timeslot 
            # overlaps at start, end, or start and end surround
            timeslots_starting_during_slot = list(models.DeviceTimeslot.objects.filter(start__range=(start, end), device_uuid__in=device_uuids))
            timeslots_ending_during_slot = list(models.DeviceTimeslot.objects.filter(stop__range=(start, end), device_uuid__in=device_uuids))
            timeslots_encompassing_slot = list(models.DeviceTimeslot.objects.filter(start__lt=start, stop__gt=end, device_uuid__in=device_uuids))
            for dts in timeslots_starting_during_slot + timeslots_ending_during_slot + timeslots_encompassing_slot:
                dts_app = dts.job.application
                # We check the nature of the timeslot.
                if db_app.is_single_tenant:
                    # If there is a single tenant claim, there is a conflict.
                    res["conflicts"][dts.device_uuid].append({
                        "start": dts.start,
                        "stop": dts.stop,
                        "reason": "Cannot schedule single-tentant on device due to existing job",
                    })
                elif dts_app.is_single_tenant:
                    res["conflicts"][dts.device_uuid].append({
                        "start": dts.start,
                        "stop": dts.stop,
                        "reason": "Single-tenant already scheduled on device",
                    })
                else:
                    dts_services = [s.service for s in dts_app.services.all()]
                    # Check if peripherals are in conflict
                    dts_app_peripherals = set(
                        p.peripheral_schema.type
                        for s in dts_services
                        for p in s.peripheral_schemas.all()
                    )
                    for peripheral in db_app_peripherals.intersection(dts_app_peripherals):
                        res["conflicts"][dts.device_uuid].append({
                            "start": dts.start,
                            "stop": dts.stop,
                            "reason": f"'{peripheral}' is already claimed on device",
                        })

                    # Check if claimed resources are in conflict
                    dts_app_resources = set(
                        r.resource.resource
                        for s in dts_services
                        for r in s.resources.all()
                    )
                    for resource in db_app_resources.intersection(dts_app_resources):
                        res["conflicts"][dts.device_uuid].append({
                            "start": dts.start,
                            "stop": dts.stop,
                            "reason": f"'{resource}' is already claimed on device",
                        })
                    # Check if node ports are in conflict
                    dts_app_ports = set(
                        p.node_port
                        for s in dts_services
                        for p in s.ports.all()
                    )
                    for port in db_app_ports.intersection(dts_app_ports):
                        res["conflicts"][dts.device_uuid].append({
                            "start": dts.start,
                            "stop": dts.stop,
                            "reason": f"Node port '{port}' is already in use on device",
                        })
    return res


def parse_javascript_iso_string(date_str):
    """
    Javascript ISO date format adds "Z" to the end, but python
    expects "+00:00". 
    """
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except Exception as e:
        LOG.error(f"Exception parsing date '{date_str}'")
        LOG.error(e)
        return None
