"""A bounded CSS-like vocabulary compiled by HA, never evaluated as browser CSS."""

import re

COLOURS = {"background", "surface", "accent", "secondary", "text", "quiet", "grid"}
NUMBERS = {
    "border-width": (1, 4),
    "icon-size": (12, 28),
    "font-size": (6, 16),
    "orbit-radius": (70, 90),
    "highlight-radius": (14, 25),
    "hub-radius": (25, 65),
    "gauge-radius": (55, 85),
    "gauge-width": (1, 12),
}
DEFAULTS = {
    "outer-border": True,
    "border-width": 2,
    "icon-size": 18,
    "font-size": 11,
    "orbit-radius": 84,
    "highlight-radius": 18,
    "hub-radius": 55,
    "gauge-radius": 70,
    "gauge-width": 6,
    "raster": "smooth",
}


def appearance(value: dict) -> dict:
    result = dict(DEFAULTS)
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
    for key, item in supplied.items():
        if key in COLOURS:
            if not isinstance(item, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", item):
                raise ValueError(f"{key} needs a #RRGGBB colour")
        elif key in NUMBERS:
            if isinstance(item, str):
                item = item.removesuffix("px")
            try:
                item = float(item)
            except (ValueError, TypeError) as error:
                raise ValueError(f"{key} needs a number") from error
            low, high = NUMBERS[key]
            if not low <= item <= high:
                raise ValueError(f"{key} must be between {low} and {high}")
            item = round(item)
        elif key == "outer-border":
            if item in ("on", "true"):
                item = True
            elif item in ("off", "false"):
                item = False
            if not isinstance(item, bool):
                raise ValueError("outer-border must be on or off")
        elif key == "raster":
            if item not in {"crisp", "smooth"}:
                raise ValueError("raster must be crisp or smooth")
        else:
            raise ValueError(f"Unsupported style property: {key}")
        result[key] = item
    return result


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
