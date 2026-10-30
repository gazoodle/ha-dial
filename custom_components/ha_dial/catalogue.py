"""Supported HA domains and Atlas presentation families."""

CONTROL_TYPES = {
    "light": ("dimmer", "CTL-LIGHT-INSTRUMENT", "mdi:lightbulb"),
    "switch": ("toggle", "CTL-SWITCH-INSTRUMENT", "mdi:toggle-switch"),
    "cover": ("position", "CTL-COVER-INSTRUMENT", "mdi:blinds"),
    "climate": ("temperature", "CTL-THERMOSTAT-INSTRUMENT", "mdi:thermometer"),
    "media_player": ("volume", "CTL-MEDIA-INSTRUMENT", "mdi:play-circle"),
    "fan": ("speed", "CTL-FAN-INSTRUMENT", "mdi:fan"),
    "alarm_control_panel": ("security", "CTL-SECURITY-INSTRUMENT", "mdi:shield-home"),
    "lock": ("access", "CTL-LOCK-INSTRUMENT", "mdi:lock"),
    "vacuum": ("cleaning", "CTL-VACUUM-INSTRUMENT", "mdi:robot-vacuum"),
    "sensor": ("readout", "CTL-ENERGY-INSTRUMENT", "mdi:chart-line"),
    "binary_sensor": ("readout", "CTL-SECURITY-INSTRUMENT", "mdi:information"),
    "weather": ("weather", "CTL-WEATHER-INSTRUMENT", "mdi:weather-partly-cloudy"),
    "timer": ("timer", "CTL-TIMER-INSTRUMENT", "mdi:timer"),
    "calendar": ("agenda", "CTL-CALENDAR-INSTRUMENT", "mdi:calendar"),
    "scene": ("scene", "CTL-SCENE-INSTRUMENT", "mdi:palette"),
    "select": ("selector", "CTL-SELECTOR-INSTRUMENT", "mdi:format-list-bulleted"),
    "input_select": ("selector", "CTL-SELECTOR-INSTRUMENT", "mdi:format-list-bulleted"),
    "number": ("number", "CTL-SELECTOR-INSTRUMENT", "mdi:numeric"),
    "input_number": ("number", "CTL-SELECTOR-INSTRUMENT", "mdi:numeric"),
    "button": ("button", "CTL-SCENE-INSTRUMENT", "mdi:gesture-tap"),
    "input_button": ("button", "CTL-SCENE-INSTRUMENT", "mdi:gesture-tap"),
}
NAV_STYLES = {
    "NAV-" + name
    for name in (
        "ORBIT",
        "POINTER",
        "ROLODEX",
        "PETALS",
        "CONSTELLATION",
        "COMPASS",
        "RIBBON",
        "BREADCRUMB",
    )
}
READOUTS = {"ENERGY", "AIR", "VEHICLE", "WATER", "DATA"}


def control_styles(domain: str) -> set[str]:
    base = CONTROL_TYPES[domain][1].removesuffix("-INSTRUMENT")
    bases = {base}
    if domain in {"sensor", "binary_sensor"}:
        bases |= {f"CTL-{name}" for name in READOUTS}
    if domain == "media_player":
        bases.add("CTL-VOLUME")
    return {
        f"{name}-{variant}" for name in bases for variant in ("INSTRUMENT", "EDITORIAL")
    }


STYLES = NAV_STYLES | {
    style for domain in CONTROL_TYPES for style in control_styles(domain)
}
