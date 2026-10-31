"""Face configuration and HA-owned source resolution; no browser/device clock semantics."""

import re
from datetime import datetime, timedelta
from math import isfinite
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .catalogue import FACE_STYLES
from .frames import resolve_frame

CLOCK_FIELDS = {
    "timezone", "world_zones", "moon_entity", "reserve_entity", "weather_entity", "metrics", "history_hours",
    "image_entity", "refresh_entity", "detection_entity",
}
METRIC_FIELDS = {"entity_id", "label", "minimum", "maximum"}
MAX_METRICS = 6
DEFAULT_ZONES = ["UTC", "Europe/London", "America/New_York", "Asia/Tokyo"]
SUN_ENTITY = "sun.sun"


def _validate_metric(metric):
    if not isinstance(metric, dict) or set(metric) - METRIC_FIELDS:
        raise ValueError("Metrics need entity_id, and optionally label, minimum and maximum")
    entity = metric.get("entity_id")
    if not isinstance(entity, str) or not re.fullmatch(r"[a-z_]+\.[a-z0-9_]{1,248}", entity):
        raise ValueError("Metrics need an HA entity")
    if not isinstance(metric.get("label", ""), str) or len(metric.get("label", "")) > 32:
        raise ValueError("Metric labels are text of at most 32 characters")
    for field in ("minimum", "maximum"):
        if field in metric and (isinstance(metric[field], bool) or not isinstance(metric[field], (int, float)) or not isfinite(metric[field])):
            raise ValueError(f"Metric {field} must be a number")
    if "minimum" in metric and "maximum" in metric and metric["minimum"] >= metric["maximum"]:
        raise ValueError("Metric minimum must be below its maximum")


def validate_clock(value):
    if not isinstance(value, dict):
        raise TypeError("Clock settings must be an object")
    if set(value) - CLOCK_FIELDS:
        raise ValueError("Unknown clock setting")
    zones = value.get("world_zones", DEFAULT_ZONES)
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
        if not isinstance(entity, str) or entity and not re.fullmatch(r"sensor\.[a-z0-9_]{1,248}", entity):
            raise ValueError("Clock complications need HA sensor entities")
    weather = value.get("weather_entity", "")
    if not isinstance(weather, str) or weather and not re.fullmatch(r"weather\.[a-z0-9_]{1,248}", weather):
        raise ValueError("The weather source needs an HA weather entity")
    image = value.get("image_entity", "")
    if not isinstance(image, str) or image and not re.fullmatch(r"(camera|image)\.[a-z0-9_]{1,248}", image):
        raise ValueError("The picture source needs an HA camera or image entity")
    for field in ("refresh_entity", "detection_entity"):
        entity = value.get(field, "")
        if not isinstance(entity, str) or entity and not re.fullmatch(r"[a-z_]+\.[a-z0-9_]{1,248}", entity):
            raise ValueError(f"{field} needs an HA entity")
    metrics = value.get("metrics", [])
    if not isinstance(metrics, list) or len(metrics) > MAX_METRICS:
        raise ValueError(f"Faces take at most {MAX_METRICS} metrics")
    for metric in metrics:
        _validate_metric(metric)
    hours = value.get("history_hours", 24)
    if isinstance(hours, bool) or not isinstance(hours, int) or not 1 <= hours <= 168:
        raise ValueError("History must cover 1 to 168 hours")


def source_entities(view: dict) -> set[str]:
    """Every entity whose change should redraw this face."""
    if view.get("style") not in FACE_STYLES:
        return set()
    settings = view.get("clock", {})
    entities = {settings.get(field) for field in ("moon_entity", "reserve_entity", "weather_entity", "refresh_entity", "detection_entity")}
    # A camera's own state event fires whenever its access token rotates, so it would act as a timer.
    # An image entity's state is its last-updated time, which is exactly the event wanted.
    if settings.get("image_entity", "").startswith("image."):
        entities.add(settings["image_entity"])
    entities |= {metric["entity_id"] for metric in settings.get("metrics", [])}
    if view["style"] in {"AMB-SOLAR", "WAT-SOLAR"}:
        entities.add(SUN_ENTITY)
    return {entity for entity in entities if entity}


def _number(state):
    try:
        value = float(state.state)
    except (AttributeError, TypeError, ValueError):
        return None
    return value if isfinite(value) else None


def _metric(hass, metric, series):
    state = hass.states.get(metric["entity_id"])
    attributes = getattr(state, "attributes", {}) or {}
    value = _number(state)
    unit = attributes.get("unit_of_measurement", "")
    minimum, maximum = metric.get("minimum"), metric.get("maximum")
    if maximum is None and unit == "%":
        minimum, maximum = 0, 100
    percent = None
    if value is not None and maximum is not None:
        low = minimum or 0
        percent = max(0, min(100, (value - low) * 100 / (maximum - low)))
    return {
        "label": metric.get("label") or attributes.get("friendly_name") or metric["entity_id"].partition(".")[2].replace("_", " "),
        "value": value,
        "text": "--" if state is None or state.state in {"unknown", "unavailable"} else f"{value:g}" if value is not None else str(state.state),
        "unit": unit,
        "percent": percent,
        "series": series.get(metric["entity_id"], []),
    }


def _sun(hass, local: datetime):
    state = hass.states.get(SUN_ENTITY)
    attributes = getattr(state, "attributes", None)
    if not attributes or "next_rising" not in attributes or "next_setting" not in attributes:
        return None
    rising = datetime.fromisoformat(str(attributes["next_rising"])).astimezone(local.tzinfo)
    setting = datetime.fromisoformat(str(attributes["next_setting"])).astimezone(local.tzinfo)
    above = state.state == "above_horizon"
    # HA reports only the next events; the current day's other bound is one day earlier, near enough
    # to place a marker. The times shown are HA's own.
    start, end = (rising - timedelta(days=1), setting) if above else (setting - timedelta(days=1), rising)
    span = (end - start).total_seconds()
    return {
        "above": above,
        "rising": rising.strftime("%H:%M"),
        "setting": setting.strftime("%H:%M"),
        "progress": max(0, min(1, (local - start).total_seconds() / span)) if span > 0 else None,
    }


def _weather(hass, entity):
    state = hass.states.get(entity) if entity else None
    if state is None or state.state in {"unknown", "unavailable"}:
        return None
    attributes = getattr(state, "attributes", {}) or {}
    temperature = attributes.get("temperature")
    return {"state": state.state, "temperature": "--" if temperature is None else f"{temperature:g}{attributes.get('temperature_unit', '°')}"}


def _detection(hass, entity):
    """What the bound entity reports, including confidence only if it reports one."""
    state = hass.states.get(entity) if entity else None
    if state is None:
        return None
    attributes = getattr(state, "attributes", {}) or {}
    label = attributes.get("friendly_name") or entity.partition(".")[2].replace("_", " ")
    active = state.state not in {"off", "unknown", "unavailable", "idle", "0"}
    score = next((attributes[name] for name in ("confidence", "score") if isinstance(attributes.get(name), (int, float))), None)
    text = f"{label} · {'DETECTED' if active else 'CLEAR'}"
    if active and score is not None:
        text += f" · {round(score * 100 if score <= 1 else score)}%"
    return {"active": active, "text": text.upper()}


def resolve_clock(hass, view, now: datetime | None = None):
    if view.get("style") not in FACE_STYLES:
        return view
    if "_clock" in view:
        return view
    from homeassistant.util import dt as dt_util

    now = now or dt_util.now()
    settings = view.get("clock", {})
    local = now.astimezone(ZoneInfo(settings["timezone"])) if settings.get("timezone") else now
    zones = settings.get("world_zones", DEFAULT_ZONES)
    moon = hass.states.get(settings.get("moon_entity", ""))
    reserve_state = hass.states.get(settings.get("reserve_entity", ""))
    reserve = None
    if reserve_state and reserve_state.attributes.get("unit_of_measurement") == "%":
        value = _number(reserve_state)
        if value is not None and 0 <= value <= 100:
            reserve = value
    data = getattr(hass, "data", {}) or {}
    series = data.get("ha_dial", {}).get("history", {}) if isinstance(data, dict) else {}
    return {
        **view,
        "_clock": {
            "hour": local.hour,
            "minute": local.minute,
            "second": local.second,
            "day": local.day,
            "weekday": local.isoweekday(),
            "days_in_month": ((local.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)).day,
            "date": local.strftime("%a %d %b").upper(),
            "weekday_name": local.strftime("%A").upper(),
            "zones": [
                (zone.rsplit("/", 1)[-1].replace("_", " ").upper(), now.astimezone(ZoneInfo(zone)).strftime("%H:%M"))
                for zone in zones
            ],
            "moon": moon.state if moon else "unavailable",
            "reserve": reserve,
            "sun": _sun(hass, local),
            "weather": _weather(hass, settings.get("weather_entity")),
            "metrics": [_metric(hass, metric, series) for metric in settings.get("metrics", [])],
            "image": resolve_frame(hass, view),
            "detection": _detection(hass, settings.get("detection_entity")),
        },
    }
