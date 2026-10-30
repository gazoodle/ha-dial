"""Clock configuration and HA-owned time resolution; no browser/device clock semantics."""

import re
from datetime import datetime
from math import isfinite
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .catalogue import CHRONOGRAPH_STYLES


def validate_clock(value):
    if not isinstance(value, dict):
        raise TypeError("Clock settings must be an object")
    if set(value) - {"timezone", "world_zones", "moon_entity", "reserve_entity"}:
        raise ValueError("Unknown clock setting")
    zones = value.get(
        "world_zones", ["UTC", "Europe/London", "America/New_York", "Asia/Tokyo"]
    )
    if not isinstance(zones, list) or not 2 <= len(zones) <= 8:
        raise ValueError("World time needs two to eight IANA time zones")
    for name in [value.get("timezone", "UTC"), *zones]:
        if not isinstance(name, str) or len(name) > 64:
            raise ValueError("Use IANA time zone names")
        try:
            ZoneInfo(name)
        except (ZoneInfoNotFoundError, ValueError) as error:
            raise ValueError(f"Unknown time zone: {name}") from error
    for field in ("moon_entity", "reserve_entity"):
        entity = value.get(field, "")
        if (
            not isinstance(entity, str)
            or entity
            and not re.fullmatch(r"sensor\.[a-z0-9_]{1,248}", entity)
        ):
            raise ValueError("Clock complications need HA sensor entities")


def resolve_clock(hass, view, now: datetime | None = None):
    if view.get("style") not in CHRONOGRAPH_STYLES:
        return view
    if "_clock" in view:
        return view
    from homeassistant.util import dt as dt_util

    now = now or dt_util.now()
    settings = view.get("clock", {})
    local = (
        now.astimezone(ZoneInfo(settings["timezone"]))
        if settings.get("timezone")
        else now
    )
    zones = settings.get(
        "world_zones", ["UTC", "Europe/London", "America/New_York", "Asia/Tokyo"]
    )
    moon = hass.states.get(settings.get("moon_entity", ""))
    reserve_state = hass.states.get(settings.get("reserve_entity", ""))
    reserve = None
    if reserve_state and reserve_state.attributes.get("unit_of_measurement") == "%":
        try:
            value = float(reserve_state.state)
            if isfinite(value) and 0 <= value <= 100:
                reserve = value
        except (ValueError, TypeError):
            pass
    return {
        **view,
        "_clock": {
            "hour": local.hour,
            "minute": local.minute,
            "second": local.second,
            "day": local.day,
            "date": local.strftime("%a %d %b").upper(),
            "zones": [
                (
                    zone.rsplit("/", 1)[-1].replace("_", " ").upper(),
                    now.astimezone(ZoneInfo(zone)).strftime("%H:%M"),
                )
                for zone in zones
            ],
            "moon": moon.state if moon else "unavailable",
            "reserve": reserve,
        },
    }
