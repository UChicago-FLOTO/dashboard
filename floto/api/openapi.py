from drf_spectacular.utils import inline_serializer, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from rest_framework import serializers

from floto.api.serializers import (
    CollectionDeviceSerializer,
    PeripheralSerializer,
    ProjectSerializer,
    TimeslotSerializer,
)

"""
Used to provide useful openapi descriptions
"""

InlineDeviceSerializer = inline_serializer(
    name="DeviceSerializer",
    fields={
        "management_access": serializers.BooleanField(
            help_text="Whether the current user can manage this device."
        ),
        "application_access": serializers.BooleanField(
            help_text="Whether the current user can schedule applications on this device."
        ),
        "is_ready": serializers.BooleanField(
            help_text="Whether applications can currently be scheduled on the device."
        ),
        "ip_address": serializers.ListField(
            child=serializers.CharField(),
            help_text="The list of ip addresses assigned to this device.",
        ),
        "mac_address": serializers.ListField(
            child=serializers.CharField(),
            help_text="The list of mac addresses assigned for this device.",
        ),
        "status": serializers.ChoiceField(
            choices=(
                ("Idle", "The device is running as expected."),
                ("retired", "This device is is retired."),
            ),
            help_text="The status of this device.",
        ),
        "latitude": serializers.DecimalField(
            max_digits=6,
            decimal_places=3,
            help_text="The latitude of this device, to 3 decimal places, fuzzed with +/- 0.005.",
        ),
        "longitude": serializers.DecimalField(
            max_digits=6,
            decimal_places=3,
            help_text="The longitude of this device, to 3 decimal places, fuzzed with +/- 0.005.",
        ),
        "peripherals": serializers.ListField(
            child=PeripheralSerializer(),
            help_text="Peripherals that are configured on this device.",
        ),
        "peripheral_resources": serializers.ListField(
            child=serializers.CharField(),
            help_text="Peripheral types that are detected as installed on this device.",
        ),
        "created_at": serializers.DateTimeField(
            help_text="When this device was first registered."
        ),
        "modified_at": serializers.DateTimeField(
            help_text="When this device was last modified."
        ),
        "api_heartbeat_state": serializers.ChoiceField(
            choices=(
                ("offline", "The API service has not heard from the device."),
                ("online", "The API service has recently heard from the device."),
                (
                    "unknown",
                    "The state of the device's connection to the API service is unknown.",
                ),
            ),
            help_text="The state of the device's connection to the API.",
        ),
        "uuid": serializers.CharField(help_text="The UUID of the device."),
        "device_name": serializers.CharField(help_text="The name of the device"),
        "note": serializers.CharField(
            help_text="Additional information about the device"
        ),
        "is_online": serializers.BooleanField(
            help_text="Whether the device is connected to the internal VPN, and the OS is working as expected."
        ),
        "last_connectivity_event": serializers.DateTimeField(
            help_text="The time of the last API connectivity event."
        ),
        "is_connected_to_vpn": serializers.BooleanField(
            help_text="Whether the device is connected to the internal VPN. This is only required for running remote commands and actions on the device."
        ),
        "last_vpn_event": serializers.DateTimeField(
            help_text="The time of the last VPN event."
        ),
        "memory_usage": serializers.IntegerField(
            help_text="The current memory usage in bytes."
        ),
        "memory_total": serializers.IntegerField(
            help_text="The total memory in bytes."
        ),
        "storage_usage": serializers.IntegerField(
            help_text="The current storage usage in bytes."
        ),
        "storage_total": serializers.IntegerField(
            help_text="The total storage in bytes."
        ),
        "cpu_usage": serializers.IntegerField(
            help_text="The current memory usage, out of 100."
        ),
        "cpu_temp": serializers.IntegerField(
            help_text="The current temperature of the CPU, in Celsius."
        ),
        "is_undervolted": serializers.BooleanField(
            help_text="Whether the device has enough power to stay on."
        ),
        "os_version": serializers.CharField(help_text="The OS version."),
        "os_variant": serializers.CharField(help_text="The OS variant."),
        "supervisor_version": serializers.CharField(
            help_text="The OS supervisor version."
        ),
    },
)

device_filter_param = OpenApiParameter(
    name="active_project",
    type=OpenApiTypes.STR,
    location=OpenApiParameter.QUERY,
    required=False,
    description="The project UUID to use when computing `management_access` and `application_access` for.",
)

obj_with_owner_filter_param = OpenApiParameter(
    name="active_project",
    type=OpenApiTypes.STR,
    location=OpenApiParameter.QUERY,
    required=False,
    description="The project UUID to use for computing view permissions of an object.",
)

InlineActionSerializer = inline_serializer(
    name="ActionSerializer",
    fields={
        "action": serializers.ChoiceField(
            help_text="The action to perform.",
            choices=(
                ("RESTART", "Request to reboot the device"),
                ("BLINK", "Blinks the device's LEDs."),
            ),
        )
    },
)

EmptyResponseSerializer = inline_serializer(
    name="NoneSerializer",
    fields={},
)

InlineLogSerializer = inline_serializer(
    name="LogSerializer",
    many=True,
    fields={
        "createdAt": serializers.IntegerField(
            help_text="Unix timestamp of when log entry was created."
        ),
        "timestamp": serializers.IntegerField(
            help_text="Unix timestamp of when log entry was created."
        ),
        "isSystem": serializers.BooleanField(
            help_text="Whether this log originates from the system."
        ),
        "isStdErr": serializers.BooleanField(
            help_text="Whether this log message was written to standard error, rather than standard output."
        ),
        "message": serializers.CharField(help_text="The log message"),
    },
)

InlineCommandSerializer = inline_serializer(
    name="CommandSerializer",
    fields={"command": serializers.CharField(help_text="The command to run.")},
)

InlineCommandResponseSerializer = inline_serializer(
    name="CommandResponseSerializer",
    fields={
        "stdout": serializers.CharField(
            help_text="The standard output of the command."
        ),
        "stderr": serializers.CharField(help_text="The standard error of the command."),
    },
)

InlineEnvironmentVariableSerializer = inline_serializer(
    name="EnvironmentVariableSerializer",
    many=True,
    fields={
        "id": serializers.IntegerField(help_text="The ID of this variable."),
        "created_at": serializers.IntegerField(
            help_text="The UNIX timestamp that this variable was created at."
        ),
        "device": serializers.CharField(
            help_text="The UUID of the device this variable is set on."
        ),
        "name": serializers.CharField(help_text="The name of this variable."),
        "value": serializers.CharField(help_text="The value of this variable."),
    },
)

InlineJobEventSerializer = inline_serializer(
    name="JobEventSerializer",
    many=True,
    fields={
        "created_at": serializers.DateTimeField(help_text="The time of the event."),
        "type": serializers.CharField(help_text="The type of event."),
        "message": serializers.CharField(help_text="The event's message."),
    },
)

InlineJobLogSerializer = inline_serializer(
    name="JobLogSerializer",
    fields={
        "device_uuid_1": serializers.JSONField(
            help_text="Per device UUID, an object with service image names as keys, with log strings as values."
        )
    },
)

InlineJobCheckSerializer = inline_serializer(
    name="JobCheckSerializer",
    fields={
        "conflicts": serializers.JSONField(
            help_text="A JSON object, with each conflicting device as a key. Values are objects of with datetime fields `start` and `stop`, along with `reason` as human-readable explanation of conflict."
        ),
        "timeslots": serializers.JSONField(
            help_text="A JSON object, with each timing string as a key. Values are objects of with datetime fields `start` and `stop`."
        ),
    },
)

InlineCollectionSerializer = inline_serializer(
    name="CollectionUpdateSerializer",
    fields={"devices": CollectionDeviceSerializer(many=True)},
)

logs_count_param = OpenApiParameter(
    name="count",
    type=OpenApiTypes.INT,
    location=OpenApiParameter.PATH,
    required=True,
    description="The number of logs to fetch.",
)

uuid_param = OpenApiParameter(
    name="id",
    type=OpenApiTypes.STR,
    location=OpenApiParameter.PATH,
    required=True,
    description="The object's UUID.",
)

InlineProjectSerializer = inline_serializer(
    name="ProjectUpdateSerializer",
    fields={
        "members": serializers.ListField(
            child=serializers.CharField(), help_text="The email of the user to add."
        ),
    },
)

InlineWrappedProjectSerializer = inline_serializer(
    name="WrappedProjectSerializer",
    fields={
        "project": ProjectSerializer(),
        "errors": serializers.ListField(
            child=serializers.CharField(),
            help_text="Errors that occurred in adding users.",
        ),
    },
)


# Inline doesn't work for this, since we are overwriting the list.
# This is a hacky workaround for the openAPI docs.
class TimeslotSummarySerializer(serializers.Serializer):
    class Meta:
        fields = ["device_uuid_1", "device_uuid_2"]

    device_uuid_1 = TimeslotSerializer(many=True)
    device_uuid_2 = TimeslotSerializer(many=True)


from_param = OpenApiParameter(
    name="from",
    type=OpenApiTypes.DATETIME,
    location=OpenApiParameter.PATH,
    required=True,
    description="Only include timeslots that end after the given time. Formatted in UTC, `YYYY-MM-DDTHH:mm:ss.sssZ`",
)

to_param = OpenApiParameter(
    name="to",
    type=OpenApiTypes.DATETIME,
    location=OpenApiParameter.PATH,
    required=True,
    description="Only include timeslots that start before the given time. Formatted in UTC, `YYYY-MM-DDTHH:mm:ss.sssZ`",
)
