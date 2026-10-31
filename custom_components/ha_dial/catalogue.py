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
    "camera": ("camera", "CAM-PORTAL", "mdi:cctv"),
    "image": ("camera", "CAM-PORTAL", "mdi:image"),
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
        # Beyond the Atlas, added on the owner's request for more variety (2026-10-31).
        "LIST",
        "GRID",
        "PAGER",
        "NEEDLE",
    )
}
READOUTS = {"ENERGY", "AIR", "VEHICLE", "WATER", "DATA"}
CHRONOGRAPH_STYLES = {f"CHR-{name}" for name in ("TRICOMPAX", "WORLDTIMER", "SKELETON", "MOONPHASE")}
AMBIENT_STYLES = {f"AMB-{name}" for name in ("SOLAR", "TYPOGRAPHIC", "ORBITAL", "STATUS")}
# Toybox was dropped by the owner on 2026-10-31.
WATCH_STYLES = {f"WAT-{name}" for name in ("CONTOUR", "MODULAR", "PALETTE", "RINGS", "SOLAR", "REFLECTIONS", "PHOTOS")}
CAMERA_STYLES = {f"CAM-{name}" for name in ("PORTAL", "CINEMA", "RADAR")}
IMAGE_STYLES = CAMERA_STYLES | {"WAT-PHOTOS"}
DATA_STYLES = {f"DAT-{name}" for name in ("AREA", "RADAR", "BANDS", "SPARK")}
# Faces resolve time and sources in HA. Only chronographs show seconds, so only they tick each second.
FACE_STYLES = CHRONOGRAPH_STYLES | AMBIENT_STYLES | WATCH_STYLES | DATA_STYLES | CAMERA_STYLES
# A camera is an entity in the tree, as a light is, so its faces are that entity's styles (2026-10-31).
PAGE_STYLES = NAV_STYLES | (FACE_STYLES - CAMERA_STYLES)
# The sources each face reads, and how many metrics it shows: the editor asks for these and no others.
CLOCK_SOURCES = ("timezone",)
FACE_SOURCES = {
    **{style: {"fields": CLOCK_SOURCES, "metrics": 0} for style in AMBIENT_STYLES | WATCH_STYLES},
    "CHR-TRICOMPAX": {"fields": CLOCK_SOURCES, "metrics": 0},
    "CHR-SKELETON": {"fields": CLOCK_SOURCES, "metrics": 0},
    "CHR-MOONPHASE": {"fields": (*CLOCK_SOURCES, "moon_entity"), "metrics": 0},
    "CHR-WORLDTIMER": {"fields": (*CLOCK_SOURCES, "world_zones", "reserve_entity"), "metrics": 0},
    "AMB-STATUS": {"fields": (*CLOCK_SOURCES, "weather_entity"), "metrics": 3},
    "WAT-PHOTOS": {"fields": (*CLOCK_SOURCES, "image_entity", "refresh_entity", "weather_entity"), "metrics": 0},
    "CAM-PORTAL": {"fields": ("refresh_entity", "action_entities"), "metrics": 0},
    "CAM-CINEMA": {"fields": ("refresh_entity",), "metrics": 0},
    "CAM-RADAR": {"fields": ("refresh_entity", "detection_entity"), "metrics": 0},
    "WAT-MODULAR": {"fields": CLOCK_SOURCES, "metrics": 3},
    "WAT-RINGS": {"fields": CLOCK_SOURCES, "metrics": 3},
    "DAT-AREA": {"fields": (*CLOCK_SOURCES, "history_hours"), "metrics": 1},
    "DAT-BANDS": {"fields": CLOCK_SOURCES, "metrics": 3},
    "DAT-RADAR": {"fields": CLOCK_SOURCES, "metrics": 6},
    "DAT-SPARK": {"fields": (*CLOCK_SOURCES, "history_hours"), "metrics": 4},
}


# Shapes that read a level or an option; every domain gets the instrument and big-type readings.
LEVEL_DOMAINS = {"light", "cover", "climate", "media_player", "fan", "number", "input_number", "select", "input_select"}


def control_styles(domain: str) -> set[str]:
    if domain in {"camera", "image"}:
        return set(CAMERA_STYLES)
    base = CONTROL_TYPES[domain][1].removesuffix("-INSTRUMENT")
    # Alternative graphics differ only as instruments; the shapes ignore the graphic, so offer them once.
    graphics = set()
    if domain in {"sensor", "binary_sensor"}:
        graphics |= {f"CTL-{name}" for name in READOUTS}
    if domain == "media_player":
        graphics.add("CTL-VOLUME")
    shapes = ("INSTRUMENT", "EDITORIAL", *(("COLUMN", "SEGMENT", "TUMBLER") if domain in LEVEL_DOMAINS else ()))
    return {f"{base}-{shape}" for shape in shapes} | {f"{name}-INSTRUMENT" for name in graphics}


STYLES = PAGE_STYLES | {
    style for domain in CONTROL_TYPES for style in control_styles(domain)
}
