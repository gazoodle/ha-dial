"""The style settings: one table that HA validates and the editor's controls are generated from.

A layout declares the settings it reads, so the dialog can only show controls with a visible
effect. tests/test_appearance_tokens.py proves each declared setting changes the scene.
"""

import re

COLOURS = {"background", "surface", "accent", "secondary", "text", "quiet", "grid"}

# name: (group, label, low, high, default)
NUMBERS = {
    "border-width": ("Frame", "Ring width", 1, 4, 2),
    "ring-inset": ("Frame", "Ring inset", 0, 12, 3),
    "ring-gap": ("Frame", "Second ring gap", 2, 10, 3),
    "tick-count": ("Frame", "Tick count", 12, 120, 60),
    "tick-length": ("Frame", "Tick length", 2, 14, 4),
    "tick-inset": ("Frame", "Tick inset", 2, 24, 7),
    "font-size": ("Type", "Title size", 8, 26, 13),
    "title-offset": ("Type", "Title position", -24, 24, 0),
    "tracking": ("Type", "Letter spacing", 0, 4, 1),
    "label-size": ("Type", "Label size", 5, 12, 6),
    "label-gap": ("Type", "Title to label gap", 8, 28, 15),
    "icon-size": ("Items", "Icon size", 10, 32, 17),
    "selected-icon-size": ("Items", "Selected icon size", 10, 40, 21),
    "item-padding": ("Items", "Icon padding", 1, 18, 6),
    "highlight-radius": ("Items", "Highlight radius", 12, 32, 20),
    "item-border": ("Items", "Item border", 1, 4, 1),
    "selected-border": ("Items", "Selected border", 1, 4, 2),
    "orbit-radius": ("Items", "Orbit radius", 56, 100, 88),
    "pointer-size": ("Items", "Pointer size", 6, 24, 13),
    "hub-radius": ("Hub", "Centre radius", 24, 72, 60),
    "hub-border": ("Hub", "Centre border", 1, 4, 1),
    "row-height": ("Rows", "Row height", 16, 40, 30),
    "row-gap": ("Rows", "Row gap", 0, 16, 5),
    "row-width": ("Rows", "Row width", 90, 190, 150),
    "row-taper": ("Rows", "Row taper", 0, 30, 12),
    "petal-length": ("Petals", "Petal length", 60, 100, 82),
    "petal-spread": ("Petals", "Petal spread", 8, 45, 22),
    "ribbon-width": ("Ribbon", "Band width", 4, 34, 19),
    "ribbon-bend": ("Ribbon", "Band bend", -40, 40, 16),
    "layer-height": ("Layers", "Layer height", 12, 34, 24),
    "layer-gap": ("Layers", "Layer gap", 2, 20, 8),
    "gauge-radius": ("Gauge", "Gauge radius", 50, 100, 74),
    "gauge-width": ("Gauge", "Value width", 1, 16, 6),
    "track-width": ("Gauge", "Track width", 1, 20, 10),
    "gauge-sweep": ("Gauge", "Sweep", 120, 320, 264),
    "gauge-tick-count": ("Gauge", "Scale ticks", 2, 41, 19),
    "gauge-tick-length": ("Gauge", "Scale tick length", 2, 14, 5),
    "gauge-tick-gap": ("Gauge", "Scale gap", 2, 20, 9),
    "value-size": ("Value", "Value size", 14, 60, 34),
    "value-offset": ("Value", "Value position", -30, 30, 0),
    "unit-size": ("Value", "Unit size", 5, 14, 8),
    "detail-size": ("Value", "Detail size", 5, 12, 7),
    "detail-offset": ("Value", "Detail position", -24, 24, 0),
    "bar-width": ("Value", "Bar width", 24, 140, 64),
    "bar-count": ("Value", "Bar segments", 4, 24, 12),
    "bar-gap": ("Value", "Bar gap", 1, 8, 3),
    "action-size": ("Actions", "Button radius", 12, 26, 17),
    "action-gap": ("Actions", "Button gap", 0, 20, 6),
    "action-offset": ("Actions", "Button position", -24, 16, 0),
    "chrome-size": ("Back and home", "Size", 8, 18, 12),
    "chrome-gap": ("Back and home", "Gap", 2, 50, 10),
    "chrome-offset": ("Back and home", "Position", -30, 18, 0),
    "hand-width": ("Hands", "Hand width", 1, 7, 3),
    "hand-length": ("Hands", "Hand length", 30, 100, 63),
}
TOGGLES = {
    "outer-border": ("Frame", "Outer ring", True),
    "ring-double": ("Frame", "Second ring", True),
    "tick-ring": ("Frame", "Tick ring", False),
    "hub-visible": ("Hub", "Show centre", True),
    "gauge-caps": ("Gauge", "Round ends", True),
    "picture-colour": ("Picture", "Colour", False),
}
CHOICES = {
    "raster": ("Rendering", "Rendering", ("smooth", "crisp"), "smooth"),
    "icon-style": ("Items", "Icons", ("outline", "filled"), "outline"),
    "chrome-style": ("Back and home", "Style", ("pill", "circle", "hidden"), "pill"),
}
# These change the treated picture, not the drawn scene, so they are proven against the frame.
FRAME_SETTINGS = {"picture-colour"}
# Crisp has no filled icons, and its pictures are always a two-colour dither.
CRISP_HIDDEN = {"icon-style", "picture-colour"}
# Crisp is its own design, not Smooth with the edges hardened.
CRISP_DEFAULTS = {"tick-ring": True, "chrome-style": "circle", "selected-border": 2, "icon-size": 16, "tracking": 2, "label-gap": 17}

DEFAULTS = {
    **{name: spec[4] for name, spec in NUMBERS.items()},
    **{name: spec[2] for name, spec in TOGGLES.items()},
    **{name: spec[3] for name, spec in CHOICES.items()},
}

_FRAME = ("outer-border", "border-width", "ring-inset", "ring-double", "ring-gap")
_CHROME = ("chrome-style", "chrome-size", "chrome-gap", "chrome-offset")
_TICKS = ("tick-ring", "tick-count", "tick-length", "tick-inset")
_TITLE = ("font-size", "title-offset", "tracking", "label-size", "label-gap")
_ICONS = ("icon-style", "icon-size", "selected-icon-size")
_ITEMS = (*_ICONS, "item-padding", "highlight-radius", "item-border", "selected-border")
_HUB = ("hub-visible", "hub-radius", "hub-border")
_GAUGE = ("gauge-radius", "gauge-width", "track-width", "gauge-sweep", "gauge-caps", "gauge-tick-count", "gauge-tick-length", "gauge-tick-gap")
_VALUE = ("value-size", "value-offset", "unit-size", "detail-size", "detail-offset")
_ACTIONS = ("action-size", "action-gap", "action-offset")
_COMMON = ("raster", *_FRAME, *_CHROME)

STYLE_SETTINGS = {
    "NAV-ORBIT": (*_TICKS, *_TITLE, *_ITEMS, *_HUB, "orbit-radius"),
    "NAV-POINTER": (*_TICKS, *_TITLE, *_ICONS, "highlight-radius", "selected-border", *_HUB, "orbit-radius", "pointer-size"),
    "NAV-ROLODEX": (*_ICONS, "font-size", "tracking", "item-border", "selected-border", "row-height", "row-gap", "row-width", "row-taper"),
    "NAV-PETALS": (*_ICONS, "font-size", "tracking", "label-size", "hub-radius", "hub-border", "petal-length", "petal-spread"),
    "NAV-CONSTELLATION": (*_ITEMS, *_TITLE, "orbit-radius"),
    "NAV-COMPASS": (*_ITEMS, *_HUB[1:], "font-size", "tracking", "orbit-radius"),
    "NAV-RIBBON": (*_ICONS, "font-size", "tracking", "item-padding", "highlight-radius", "item-border", "selected-border", "ribbon-width", "ribbon-bend"),
    "NAV-BREADCRUMB": ("font-size", "tracking", "label-size", "layer-height", "layer-gap", "selected-border"),
    "NAV-LIST": (*_ICONS, "font-size", "tracking", "selected-border", "row-height", "row-gap"),
    "NAV-GRID": (*_ICONS, "font-size", "tracking", "item-padding", "item-border", "selected-border", "row-gap"),
    "NAV-PAGER": ("icon-style", "selected-icon-size", "highlight-radius", "selected-border", "font-size", "title-offset", "tracking"),
    "NAV-NEEDLE": (*_ICONS, "font-size", "tracking", "orbit-radius", "selected-border"),
    "CHR": (*_TICKS, "hand-width", "hand-length"),
    "CHR-SKELETON": _TICKS,  # Its time is in separate registers, so it has no central hands.
    "AMB-TYPOGRAPHIC": (*_TICKS, "value-size", "title-offset", "tracking", "label-size"),
    "AMB-SOLAR": ("gauge-radius", "gauge-width", "track-width", "value-size", "title-offset", "label-size"),
    "AMB-ORBITAL": ("gauge-radius", "value-size", "title-offset", "label-size"),
    "AMB-STATUS": ("value-size", "title-offset", "label-size"),
    "WAT-CONTOUR": ("gauge-radius", "value-size", "title-offset", "label-size"),
    "WAT-MODULAR": ("value-size", "label-size"),
    "WAT-PALETTE": ("gauge-radius", "gauge-width", "value-size", "label-size"),
    "WAT-RINGS": ("gauge-width",),
    "WAT-SOLAR": ("value-size", "title-offset", "label-size"),
    "WAT-REFLECTIONS": ("value-size", "label-size"),
    "WAT-PHOTOS": ("value-size", "title-offset", "label-size"),
    "CAM-PORTAL": ("picture-colour",),
    "CAM-CINEMA": ("label-size", "tracking"),
    "CAM-RADAR": ("picture-colour", "label-size", "tracking"),
    "DAT-AREA": ("value-size", "label-size"),
    "DAT-RADAR": ("label-size",),
    "DAT-BANDS": ("gauge-radius", "gauge-width", "value-size", "label-size"),
    "DAT-SPARK": ("value-size",),
    "CTL-INSTRUMENT": (*_GAUGE, *_VALUE, *_ACTIONS, "selected-icon-size", "icon-style", "tracking"),
    "CTL-EDITORIAL": (*_VALUE, *_ACTIONS, "selected-icon-size", "icon-style", "tracking", "font-size"),
    "CTL-COLUMN": (*_VALUE, *_ACTIONS, "bar-width", "bar-count", "bar-gap", "selected-icon-size", "icon-style", "tracking", "selected-border"),
    "CTL-SEGMENT": (*_GAUGE[:3], "bar-count", "bar-gap", *_VALUE, *_ACTIONS, "selected-icon-size", "icon-style", "tracking"),
    "CTL-TUMBLER": (*_VALUE, *_ACTIONS, "row-height", "row-width", "selected-border", "selected-icon-size", "icon-style", "tracking"),
}


def style_family(style: str) -> str:
    """Map a style to its declared settings: every domain shares a control shape's settings."""
    if style in STYLE_SETTINGS:
        return style
    if style.startswith("CHR-"):
        return "CHR"
    if style.startswith("CTL-"):
        return "CTL-" + style.rsplit("-", 1)[-1]
    return style if style in STYLE_SETTINGS else "NAV-ORBIT"


def style_settings(style: str, raster: str = "smooth") -> tuple:
    """Settings with a visible effect for this style in this mode."""
    settings = (*_COMMON, *STYLE_SETTINGS[style_family(style)])
    return tuple(name for name in settings if not (raster == "crisp" and name in CRISP_HIDDEN))


def _validated(key, item):
    if key in COLOURS:
        if not isinstance(item, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", item):
            raise ValueError(f"{key} needs a #RRGGBB colour")
        return item
    if key in NUMBERS:
        if isinstance(item, str):
            item = item.removesuffix("px")
        try:
            item = float(item)
        except (ValueError, TypeError) as error:
            raise ValueError(f"{key} needs a number") from error
        low, high = NUMBERS[key][2:4]
        if not low <= item <= high:
            raise ValueError(f"{key} must be between {low} and {high}")
        return round(item)
    if key in TOGGLES:
        if item in ("on", "true"):
            item = True
        elif item in ("off", "false"):
            item = False
        if not isinstance(item, bool):
            raise ValueError(f"{key} must be on or off")
        return item
    if key in CHOICES:
        if item not in CHOICES[key][2]:
            raise ValueError(f"{key} must be one of {', '.join(CHOICES[key][2])}")
        return item
    raise ValueError(f"Unsupported style property: {key}")


def appearance(value: dict) -> dict:
    declarations = value.get("css", "")
    if not isinstance(declarations, str) or len(declarations) > 4096:
        raise ValueError("Style declarations must be text of at most 4096 characters")
    supplied = dict(value.get("appearance", {}))
    for declaration in declarations.split(";"):
        if not declaration.strip():
            continue
        key, separator, text = declaration.partition(":")
        if not separator:
            raise ValueError("Use property: value; in Advanced style")
        supplied[key.strip()] = text.strip()
    validated = {key: _validated(key, item) for key, item in supplied.items()}
    crisp = validated.get("raster", DEFAULTS["raster"]) == "crisp"
    return {**DEFAULTS, **(CRISP_DEFAULTS if crisp else {}), **validated}


def validate_options(value: dict) -> None:
    if "clock" in value:
        from .chronograph import validate_clock

        validate_clock(value["clock"])
    if not isinstance(value.get("appearance", {}), dict):
        raise TypeError("Appearance must be an object")
    appearance(value)
    if "confirm" in value and not isinstance(value["confirm"], bool):
        raise TypeError("Confirm actions must be on or off")
    icon = value.get("icon", "")
    if not isinstance(icon, str) or icon and not re.fullmatch(r"mdi:[a-z0-9-]+", icon):
        raise ValueError("Icons use mdi:name")
    if icon:
        from .assets import icon_names

        if icon not in icon_names():
            raise ValueError(f"Unknown bundled MDI icon: {icon}")
    if not isinstance(value.get("conditions", []), list):
        raise TypeError("Visibility conditions must be a list")

    from .visibility import templates

    templates(value.get("conditions", []))
