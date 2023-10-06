from django.db.models import Q
from rest_framework.exceptions import ValidationError
from datetime import datetime, timedelta
import logging


LOG = logging.getLogger(__name__)


def filter_by_created_by_or_public(queryset, request):
    return queryset.filter(Q(created_by=request.user) | Q(is_public=True))


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
        return [(datetime.now(), datetime.now() + parse_on_demand_args(args))]
    else:
        raise ValidationError(f"Invalid timing string {value}")