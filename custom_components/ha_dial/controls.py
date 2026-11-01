"""Domain state and actions; no rendering or navigation decisions."""

from homeassistant.components.cover import CoverEntityFeature
from homeassistant.core import State

from .domain_controls import extended_command, extended_state


def control_state(entity_id: str, state: State | None) -> dict:
    domain = entity_id.partition(".")[0]
    available = state is not None and state.state not in {"unknown", "unavailable"}
    attributes = state.attributes if state else {}
    active = (
        state is not None
        and available
        and state.state in {"on", "open", "opening", "closing"}
    )
    value = 100 if active else 0
    actions = []
    continuous = False
    position_known = True
    if domain == "light":
        brightness = attributes.get("brightness")
        if isinstance(brightness, (int, float)):
            value = round(brightness * 100 / 255)
        modes = attributes.get("supported_color_modes", [])
        continuous = bool(set(modes) - {"onoff", "unknown"}) if modes else True
    elif domain == "cover":
        features = attributes.get("supported_features", 0)
        actions = [
            action
            for action, feature in (
                ("open", CoverEntityFeature.OPEN),
                ("stop", CoverEntityFeature.STOP),
                ("close", CoverEntityFeature.CLOSE),
            )
            if features & feature
        ]
        position = attributes.get("current_position")
        position_known = isinstance(position, (int, float))
        if isinstance(position, (int, float)):
            value = round(position)
        continuous = bool(features & CoverEntityFeature.SET_POSITION) and position_known
    extra = (
        extended_state(domain, state, available)
        if domain not in {"light", "switch", "cover"}
        else {}
    )
    return {
        "value": max(0, min(100, value)),
        "active": bool(active),
        "available": available,
        "title": attributes.get("friendly_name"),
        "continuous": continuous,
        "actions": actions,
        "position_known": position_known,
        "state": state.state if available and state is not None else "unavailable",
        **({"device_class": attributes.get("device_class")} if domain == "cover" else {}),
        **extra,
    }


def control_command(
    view: dict, action: str, item: str | None
) -> tuple[str, str, dict] | None:
    if not view.get("available") or action not in {
        "press",
        "touch",
        "rotate_left",
        "rotate_right",
        "set_value",
    }:
        return None
    domain = view["entity_id"].partition(".")[0]
    stopping = domain == "cover" and (action == "press" or item == "stop")
    if (
        action in {"press", "touch"}
        and (view.get("confirm") or domain in {"lock", "alarm_control_panel"})
        and not view.get("_confirmed")
        and not stopping
    ):
        return None
    if view.get("confirmation") and not view.get("_confirmed"):
        return None
    if domain not in {"light", "switch", "cover"}:
        return extended_command(
            view,
            "touch" if view.get("_confirmed") else action,
            view.get("_confirmed") or item,
        )
    data = {"entity_id": view["entity_id"]}
    if action in {"rotate_left", "rotate_right", "set_value"} and view.get(
        "continuous"
    ):
        if domain == "light":
            return domain, "turn_on", {**data, "brightness_pct": view["value"]}
        if domain == "cover":
            return (
                domain,
                "set_cover_position",
                {**data, "position": round(view["value"])},
            )
    if domain == "cover":
        if view.get("_confirmed"):
            action, item = "touch", view["_confirmed"]
        command = "stop" if action == "press" else item if action == "touch" else None
        if command in view.get("actions", []):
            return domain, f"{command}_cover", data
    elif action == "press":
        return domain, "turn_on" if view["active"] else "turn_off", data
    return None


def preview_feedback(control: dict, action: str, item: str | None) -> None:
    """Simulate cover results without calling services from a draft card."""
    command = control_command(control, action, item)
    if command is None:
        return
    if command[0] != "cover":
        domain, service, data = command
        if domain == "climate" and service == "set_hvac_mode":
            control["state"] = data["hvac_mode"]
        elif domain == "fan" and service == "set_preset_mode":
            control["detail"] = data["preset_mode"]
        elif domain in {"select", "input_select"}:
            control["state"] = data["option"]
        elif domain == "lock":
            control["state"] = "locked" if service == "lock" else "unlocked"
        elif domain == "alarm_control_panel":
            control["state"] = (
                "disarmed"
                if service == "alarm_disarm"
                else service.replace("alarm_arm_", "armed_")
            )
        elif domain == "media_player" and service == "media_play_pause":
            control["state"] = "paused" if control["state"] == "playing" else "playing"
        elif domain == "media_player" and service == "volume_mute":
            control["muted"] = data["is_volume_muted"]
        elif domain == "timer":
            control["state"] = {"start": "active", "pause": "paused", "cancel": "idle"}[
                service
            ]
        elif domain == "vacuum":
            control["state"] = {
                "start": "cleaning",
                "pause": "paused",
                "stop": "idle",
                "return_to_base": "returning",
            }[service]
        elif domain in {"scene", "button", "input_button"}:
            control["detail"] = "Preview action only"
        return
    service = command[1]
    if service in {"open_cover", "close_cover"}:
        control["value"] = 100 if service == "open_cover" else 0
    control["active"] = control["value"] > 0
    control["state"] = "open" if control["active"] else "closed"
    control["position_known"] = True
