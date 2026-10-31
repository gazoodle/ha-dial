"""Compile a saved Dial definition and current navigation state into a scene."""

from __future__ import annotations

from .appearance import appearance
from .canvas import Canvas
from .catalogue import CHRONOGRAPH_STYLES, FACE_STYLES
from .chronograph_layout import chronograph_layout
from .control_layout import control_layout
from .face_layout import face_layout
from .navigation_layout import chrome, navigation_layout

MAX_VIEW_BYTES = 24576

THEMES = {
    "ember": {"bg": "#060707", "surface": "#15110f", "primary": "#ff8b2d", "secondary": "#ffd19a", "quiet": "#77513a", "text": "#fff7eb", "grid": "#3a2920"},
    "verdant": {"bg": "#030a09", "surface": "#071815", "primary": "#66f7ba", "secondary": "#b9ffe2", "quiet": "#2a6655", "text": "#effff8", "grid": "#153b32"},
    "cobalt": {"bg": "#050711", "surface": "#0b1025", "primary": "#5aa8ff", "secondary": "#b7c9ff", "quiet": "#32477b", "text": "#f4f6ff", "grid": "#1c2a55"},
    "rose": {"bg": "#0b0608", "surface": "#201015", "primary": "#ff719e", "secondary": "#ffd0c2", "quiet": "#76384d", "text": "#fff3f5", "grid": "#46222f"},
    "acid": {"bg": "#070904", "surface": "#151a0a", "primary": "#c9ff45", "secondary": "#fff186", "quiet": "#5c7425", "text": "#fbffe9", "grid": "#344214"},
    "alloy": {"bg": "#060708", "surface": "#181b1f", "primary": "#e4e9ed", "secondary": "#8fd8ff", "quiet": "#59636c", "text": "#ffffff", "grid": "#30363c"},
}
OVERRIDES = {"background": "bg", "accent": "primary", "surface": "surface", "secondary": "secondary", "text": "text", "quiet": "quiet", "grid": "grid"}


def _frame(c: Canvas, o: dict) -> None:
    if not o["outer-border"]:
        return
    radius = 119 - o["ring-inset"]
    c.ring(120, 120, radius, c.theme["primary"], o["border-width"])
    if o["ring-double"]:
        c.ring(120, 120, radius - o["border-width"] - o["ring-gap"] + 1, c.tint(0.45))


def _settings_cog(c: Canvas, view: dict, y: int) -> dict | None:
    items = view.get("items", [])
    if not any(item.get("settings") for item in items):
        return None
    active = view.get("selected", 0) == len(items) - 1
    fill = c.theme["bg"] if c.crisp else c.theme["surface"]
    c.disc(120, y, 15, fill, c.theme["primary"] if active else c.theme["quiet"])
    c.icon("mdi:cog-outline", 120, y, 18, c.theme["secondary"] if active else c.theme["text"], fill)
    return {"id": "__settings", "x": 120, "y": y, "r": 17}


def compile_scene(view: dict) -> dict:
    """Return bounded, pixel-positioned drawing instructions for both renderers."""
    theme = dict(THEMES.get(view.get("theme", "ember"), THEMES["ember"]))
    options = appearance(view)
    for key, target in OVERRIDES.items():
        if key in options:
            theme[target] = options[key]

    c = Canvas(theme, options["raster"] == "crisp")
    _frame(c, options)
    style = view.get("style", "NAV-ORBIT")
    if style in CHRONOGRAPH_STYLES:
        regions = chronograph_layout(c, view, options)
        regions = regions + chrome(c, view, options, 212)
        cog = 24
    elif style in FACE_STYLES:
        regions = face_layout(c, view, options)
        regions = regions + chrome(c, view, options, 212)
        cog = 30
    elif view.get("kind") in {"control", "settings"} or style.startswith("CTL-"):
        regions = control_layout(c, view, options)
        regions = regions + chrome(c, view, options, 212)
        cog = None
    else:
        regions, cog = navigation_layout(c, view, options)
    if cog is not None and (settings := _settings_cog(c, view, cog)):
        regions.append(settings)

    return {
        "version": 5,
        "width": 240,
        "height": 240,
        "background": theme["bg"],
        "label": view.get("title", "HA Dial"),
        "screen": view.get("id", "root"),
        "elements": c.elements,
        "regions": regions,
    }
