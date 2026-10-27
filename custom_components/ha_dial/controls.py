"""Domain state and actions; no rendering or navigation decisions."""

from homeassistant.components.cover import CoverEntityFeature
from homeassistant.core import State


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
    return {
        "value": max(0, min(100, value)),
        "active": bool(active),
        "available": available,
        "title": attributes.get("friendly_name"),
        "continuous": continuous,
        "actions": actions,
        "position_known": position_known,
        "state": state.state if available and state is not None else "unavailable",
    }


def control_command(
    view: dict, action: str, item: str | None
) -> tuple[str, str, dict] | None:
    if not view.get("available"):
        return None
    domain = view["entity_id"].partition(".")[0]
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
        command = "stop" if action == "press" else item if action == "touch" else None
        if command in view.get("actions", []):
            return domain, f"{command}_cover", data
    elif action == "press":
        return domain, "turn_on" if view["active"] else "turn_off", data
    return None


def preview_feedback(control: dict, action: str, item: str | None) -> None:
    """Simulate cover results without calling services from a draft card."""
    command = control_command(control, action, item)
    if command is None or command[0] != "cover":
        return
    service = command[1]
    if service in {"open_cover", "close_cover"}:
        control["value"] = 100 if service == "open_cover" else 0
    control["active"] = control["value"] > 0
    control["state"] = "open" if control["active"] else "closed"
    control["position_known"] = True
