"""HA domain semantics for the Atlas controls beyond light, switch and cover."""

import math

READ_ONLY = {"sensor", "binary_sensor", "weather", "calendar", "camera", "image"}
CONFIRM = {"lock", "alarm_control_panel", "scene", "button", "input_button"}


def extended_state(domain, state, available):
    a = state.attributes if state else {}
    status = state.state if available else "unavailable"
    value, minimum, maximum, step, unit = 0, 0, 100, 5, "%"
    continuous, actions, options = False, [], []
    battery = None
    if domain == "climate":
        value, minimum, maximum = (
            a.get("temperature", 20),
            a.get("min_temp", 7),
            a.get("max_temp", 35),
        )
        step, unit = a.get("target_temp_step", 0.5), a.get("temperature_unit", "°")
        continuous = (
            available
            and bool(a.get("supported_features", 0) & 1)
            and isinstance(a.get("temperature"), (float, int))
        )
        options = a.get("hvac_modes", [])
        actions = ["mode"] if options else []
        detail = f"Ambient {a.get('current_temperature', '--')}{unit}"
    elif domain == "media_player":
        value = round((a.get("volume_level") or 0) * 100)
        continuous = bool(a.get("supported_features", 0) & 4)
        actions = [
            name
            for name, flag in [
                ("play_pause", 16385),
                ("previous", 16),
                ("next", 32),
                ("mute", 8),
            ]
            if available and a.get("supported_features", 0) & flag
        ]
        detail = a.get("media_title", status)
    elif domain == "fan":
        value = a.get("percentage", 0)
        continuous = bool(a.get("supported_features", 0) & 1)
        step = a.get("percentage_step", 5)
        actions = ["toggle"]
        options = a.get("preset_modes", [])
        if options:
            actions.append("preset")
        detail = a.get("preset_mode", status)
    elif domain in {"number", "input_number"}:
        value, minimum, maximum = status, a.get("min", 0), a.get("max", 100)
        step, unit, continuous = (
            a.get("step", 1),
            a.get("unit_of_measurement", ""),
            True,
        )
        detail = status
    elif domain in {"select", "input_select"}:
        options = a.get("options", [])
        value = options.index(status) if status in options else 0
        maximum, step, unit, continuous = (
            max(0, len(options) - 1),
            1,
            "",
            len(options) > 1,
        )
        detail = status
    else:
        detail = status
        if domain == "lock":
            actions = (
                ["lock" if status == "unlocked" else "unlock"]
                if not a.get("code_format")
                else []
            )
        elif domain == "alarm_control_panel":
            # No PIN is accepted or persisted by this controller.
            actions = (
                ["disarm"]
                if status.startswith("armed_") and not a.get("code_format")
                else []
            )
            if status == "disarmed" and not a.get("code_arm_required", True):
                features = a.get("supported_features", 0)
                actions = [
                    name
                    for name, bit in [
                        ("arm_home", 1),
                        ("arm_away", 2),
                        ("arm_night", 4),
                        ("arm_vacation", 32),
                    ]
                    if features & bit
                ]
        elif domain == "vacuum":
            features = a.get("supported_features", 0)
            actions = [
                name
                for name, bit in [
                    ("start", 8192),
                    ("pause", 4),
                    ("stop", 8),
                    ("dock", 16),
                ]
                if features & bit
            ]
            detail = f"{status} / {a.get('battery_level', '--')}%"
            battery = a.get("battery_level")
        elif domain == "timer":
            actions = ["start", "pause", "cancel"]
            detail = a.get("remaining", a.get("duration", status))
        elif domain == "scene":
            actions = ["activate"]
        elif domain in {"button", "input_button"}:
            actions = ["press"]
        elif domain == "weather":
            detail = f"{a.get('temperature', '--')}{a.get('temperature_unit', '°')} / {status}"
        elif domain == "calendar":
            detail = a.get("message", "No event")
        elif domain == "sensor":
            value, unit = status, a.get("unit_of_measurement", "")
    try:
        value = float(value)
        if not math.isfinite(value):
            value = 0
    except (ValueError, TypeError):
        value = 0

    def finite(number, fallback):
        try:
            return float(number) if math.isfinite(float(number)) else fallback
        except (ValueError, TypeError):
            return fallback

    minimum, maximum = finite(minimum, 0), finite(maximum, 100)
    if maximum < minimum:
        minimum, maximum = maximum, minimum
    step = max(0.01, finite(step, 1))
    return {
        "value": max(minimum, min(maximum, value)) if continuous else value,
        "numeric_value": domain != "sensor" or _is_numeric(status),
        "muted": a.get("is_volume_muted", False),
        "minimum": minimum,
        "maximum": maximum,
        "step": step,
        "unit": unit,
        "continuous": bool(available and continuous and maximum > minimum),
        "actions": actions if available else [],
        "options": options,
        "detail": str(detail or status),
        "state": status,
        "confirm": domain in CONFIRM,
        "battery": finite(battery, None) if battery is not None else None,
        "active": status not in {"off", "idle", "unlocked", "disarmed", "unavailable"},
    }


def extended_command(view, action, item):
    domain = view["domain"]
    data = {"entity_id": view["entity_id"]}
    if domain in READ_ONLY:
        return None
    if action in {"rotate_left", "rotate_right", "set_value"} and view.get(
        "continuous"
    ):
        value = view["value"]
        if domain == "climate":
            return domain, "set_temperature", {**data, "temperature": value}
        if domain == "media_player":
            return domain, "volume_set", {**data, "volume_level": value / 100}
        if domain == "fan":
            return domain, "set_percentage", {**data, "percentage": round(value)}
        if domain in {"number", "input_number"}:
            return domain, "set_value", {**data, "value": value}
        if domain in {"select", "input_select"} and view.get("options"):
            return (
                domain,
                "select_option",
                {**data, "option": view["options"][round(value)]},
            )
    command = (
        item
        if action == "touch"
        else view.get("actions", [None])[0]
        if action == "press" and view.get("actions")
        else None
    )
    if not isinstance(command, str) or command not in view.get("actions", []):
        return None
    if domain == "climate" and command == "mode":
        options = view["options"]
        current = view.get("state")
        return (
            domain,
            "set_hvac_mode",
            {
                **data,
                "hvac_mode": options[(options.index(current) + 1) % len(options)]
                if current in options
                else options[0],
            },
        )
    if domain == "fan" and command == "preset":
        options = view["options"]
        current = view.get("detail")
        return (
            domain,
            "set_preset_mode",
            {
                **data,
                "preset_mode": options[(options.index(current) + 1) % len(options)]
                if current in options
                else options[0],
            },
        )
    if domain == "media_player":
        if command == "mute":
            return (
                domain,
                "volume_mute",
                {**data, "is_volume_muted": not view.get("muted", False)},
            )
        command = {
            "play_pause": "media_play_pause",
            "previous": "media_previous_track",
            "next": "media_next_track",
        }[command]
    elif domain == "alarm_control_panel":
        command = "alarm_" + command
    elif domain == "vacuum" and command == "dock":
        command = "return_to_base"
    elif domain == "scene":
        command = "turn_on"
    return domain, command, data


def _is_numeric(value):
    try:
        return math.isfinite(float(value))
    except (ValueError, TypeError):
        return False
