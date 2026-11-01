"""What a light's turn adjusts: brightness, white temperature or colour. No drawing or HA here.

Each mode is just a value, range and step, so firmware's local turn handling needs no change.
"""

from colorsys import hsv_to_rgb
from math import log

BRIGHTNESS, WHITE, COLOUR = "brightness", "white", "colour"
COLOUR_MODES = {"hs", "xy", "rgb", "rgbw", "rgbww"}
DEFAULT_KELVIN = (2000, 6500)
KELVIN_STEP = 100
HUE_STEP = 10


def abilities(attributes: dict) -> dict:
    """What a light can do and is doing, as far as its attributes say."""
    modes = set(attributes.get("supported_color_modes") or [])
    low = attributes.get("min_color_temp_kelvin") or DEFAULT_KELVIN[0]
    high = attributes.get("max_color_temp_kelvin") or DEFAULT_KELVIN[1]
    kelvin = attributes.get("color_temp_kelvin")
    colour = attributes.get("hs_color")
    return {
        "white": "color_temp" in modes,
        "colour": bool(modes & COLOUR_MODES),
        "kelvin_min": low,
        "kelvin_max": high,
        # A light that's off reports neither, so start somewhere it can actually show.
        "kelvin": kelvin if isinstance(kelvin, (int, float)) else round((low + high) / 200) * 100,
        "hue": colour[0] if colour else 0,
        "saturation": colour[1] if colour else 100,
    }


def available_modes(light: dict) -> list[str]:
    return [BRIGHTNESS, *([WHITE] if light.get("white") else []), *([COLOUR] if light.get("colour") else [])]


def mode_fields(mode: str, light: dict, brightness: float) -> dict:
    """The value and range a control shows and turns while in this mode."""
    if mode == WHITE:
        return {"value": round(light["kelvin"]), "minimum": light["kelvin_min"], "maximum": light["kelvin_max"], "step": KELVIN_STEP, "unit": "K", "detail": "WHITE"}
    if mode == COLOUR:
        return {"value": round(light["hue"]), "minimum": 0, "maximum": 359, "step": HUE_STEP, "unit": "°", "detail": "COLOUR"}
    return {"value": brightness, "minimum": 0, "maximum": 100, "step": 5, "unit": "%"}


def remember(light: dict, mode: str, value: float) -> None:
    """Keep what was turned to, so leaving a mode and coming back finds it there."""
    if mode == WHITE:
        light["kelvin"] = value
    elif mode == COLOUR:
        light["hue"] = value


def service_data(mode: str, light: dict, value: float) -> dict:
    if mode == WHITE:
        return {"color_temp_kelvin": round(value)}
    if mode == COLOUR:
        # At no saturation every hue looks white, and turning would seem to do nothing.
        return {"hs_color": [round(value), light.get("saturation") or 100]}
    return {"brightness_pct": value}


def _hex(red: float, green: float, blue: float) -> str:
    return "#" + "".join(f"{max(0, min(255, round(part))):02x}" for part in (red, green, blue))


def kelvin_colour(kelvin: float) -> str:
    """An approximation of a white's colour, after Tanner Helland's fit of black-body data."""
    t = kelvin / 100
    if t > 66:
        return _hex(329.7 * (t - 60) ** -0.1332, 288.12 * (t - 60) ** -0.0755, 255)
    return _hex(255, 99.47 * log(t) - 161.12, 138.52 * log(t - 10) - 305.04 if t > 19 else 0)


def hue_colour(hue: float) -> str:
    return _hex(*(part * 255 for part in hsv_to_rgb(hue / 360, 1, 1)))


def colour_at(view: dict, fraction: float) -> str | None:
    """The colour part-way along this mode's range, or None for brightness, which has no colour of its own."""
    mode = view.get("light_mode")
    low, high = view.get("minimum", 0), view.get("maximum", 100)
    if mode == WHITE:
        return kelvin_colour(low + (high - low) * fraction)
    if mode == COLOUR:
        return hue_colour(low + (high - low) * fraction)
    return None


def current_colour(view: dict) -> str | None:
    low, high = view.get("minimum", 0), view.get("maximum", 100)
    span = high - low
    return colour_at(view, (view.get("value", low) - low) / span) if span > 0 else None
