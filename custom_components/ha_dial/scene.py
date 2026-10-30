"""Compile a saved Dial definition and current navigation state into a scene."""

from __future__ import annotations

from math import cos, pi, sin

from .appearance import appearance
from .assets import _number_mask, _text_mask, icon_mask
from .catalogue import CONTROL_TYPES
from .control_layout import control_layout
from .navigation_layout import navigation_layout

MAX_VIEW_BYTES = 24576

THEMES = {
    "ember": {
        "bg": "#060707",
        "surface": "#15110f",
        "primary": "#ff8b2d",
        "secondary": "#ffd19a",
        "quiet": "#77513a",
        "text": "#fff7eb",
        "grid": "#3a2920",
    },
    "verdant": {
        "bg": "#030a09",
        "surface": "#071815",
        "primary": "#66f7ba",
        "secondary": "#b9ffe2",
        "quiet": "#2a6655",
        "text": "#effff8",
        "grid": "#153b32",
    },
    "cobalt": {
        "bg": "#050711",
        "surface": "#0b1025",
        "primary": "#5aa8ff",
        "secondary": "#b7c9ff",
        "quiet": "#32477b",
        "text": "#f4f6ff",
        "grid": "#1c2a55",
    },
    "rose": {
        "bg": "#0b0608",
        "surface": "#201015",
        "primary": "#ff719e",
        "secondary": "#ffd0c2",
        "quiet": "#76384d",
        "text": "#fff3f5",
        "grid": "#46222f",
    },
    "acid": {
        "bg": "#070904",
        "surface": "#151a0a",
        "primary": "#c9ff45",
        "secondary": "#fff186",
        "quiet": "#5c7425",
        "text": "#fbffe9",
        "grid": "#344214",
    },
    "alloy": {
        "bg": "#060708",
        "surface": "#181b1f",
        "primary": "#e4e9ed",
        "secondary": "#8fd8ff",
        "quiet": "#59636c",
        "text": "#ffffff",
        "grid": "#30363c",
    },
}


def _point(cx: int, cy: int, radius: int, degrees: float) -> tuple[float, float]:
    angle = (degrees - 90) * pi / 180
    return cx + cos(angle) * radius, cy + sin(angle) * radius


def compile_scene(view: dict) -> dict:
    """Return bounded, pixel-positioned drawing instructions for both renderers."""
    theme = THEMES.get(view.get("theme", "ember"), THEMES["ember"])
    theme = dict(theme)
    options = appearance(view)
    for key, target in {
        "background": "bg",
        "accent": "primary",
        "surface": "surface",
        "secondary": "secondary",
        "text": "text",
        "quiet": "quiet",
        "grid": "grid",
    }.items():
        if key in options:
            theme[target] = options[key]
    raster = options["raster"]
    items = view.get("items", [])
    selected = view.get("selected", 0)
    elements = (
        [
            {
                "op": "circle",
                "x": 120,
                "y": 120,
                "r": 116,
                "stroke": theme["primary"],
                "width": options["border-width"],
            }
        ]
        if options["outer-border"]
        else []
    )
    regions = [{"id": "back", "x": 90, "y": 158, "r": 16}] if view.get("back") else []
    regions.append({"id": "home", "x": 150, "y": 158, "r": 16})

    def line(x1: float, y1: float, x2: float, y2: float, colour: str) -> dict:
        return {
            "op": "line",
            "x1": round(x1),
            "y1": round(y1),
            "x2": round(x2),
            "y2": round(y2),
            "stroke": colour,
        }

    extended = view.get("kind") in {"control", "settings"} and (
        view.get("domain", "light") not in {"light", "switch", "cover"}
        or view.get("style", "").endswith("-EDITORIAL")
        or view.get("confirmation")
    )
    if extended:
        body, targets = control_layout(
            {
                **view,
                "_raster": raster,
                "_font_size": options["font-size"],
                "_icon_size": options["icon-size"],
                "_gauge_radius": options["gauge-radius"],
                "_gauge_width": options["gauge-width"],
            },
            theme,
        )
        elements.extend(body)
        regions = (
            targets
            + ([{"id": "back", "x": 90, "y": 212, "r": 16}] if view.get("back") else [])
            + [{"id": "home", "x": 150, "y": 212, "r": 16}]
        )
    elif view.get("style", "NAV-ORBIT").startswith("CTL-"):
        domain = view.get("domain", "light")
        elements.append(
            {
                "op": "icon",
                "x": 120,
                "y": 65,
                "size": options["icon-size"],
                "icon": view.get("icon")
                or CONTROL_TYPES.get(domain, (None, None, "mdi:information"))[2],
                "colour": theme["primary"],
            }
        )
        value = view.get("value", 0)
        available = view.get("available", True)
        active = available and view.get("active", False)
        accent = theme["primary"] if active or view.get("pending") else theme["quiet"]
        status = (
            "UNAVAILABLE"
            if not available
            else "PENDING"
            if view.get("pending")
            else str(view.get("state", "OPEN" if active else "CLOSED")).upper()
            if domain == "cover"
            else "ON"
            if active
            else "OFF"
        )
        if domain == "light" and available and not view.get("pending"):
            status = "BRIGHTNESS / " + status
        centre = (
            ("ON" if active else "OFF")
            if domain == "switch"
            else (str(round(value)) if view.get("position_known", True) else "--")
        )
        elements.extend(
            [
                {
                    "op": "mask",
                    "x": 120,
                    "y": 24,
                    "text": domain.upper(),
                    "size": 8,
                    "colour": theme["secondary"],
                },
                {
                    "op": "mask",
                    "x": 120,
                    "y": 88,
                    "text": view.get("title", "Light"),
                    "size": 9,
                    "colour": theme["text"],
                },
                {
                    "op": "arc",
                    "x": 120,
                    "y": 118,
                    "r": options["gauge-radius"],
                    "start": -132,
                    "end": 132,
                    "stroke": theme["grid"],
                    "width": 10,
                },
                {
                    "op": "gauge",
                    "fill": theme["primary"],
                    "x": 120,
                    "y": 118,
                    "r": options["gauge-radius"],
                    "start": -132,
                    "end": 132,
                    "value": round(value),
                    "stroke": accent,
                    "width": options["gauge-width"],
                },
                {
                    **(
                        {
                            "op": "number",
                            "value": round(value),
                            **_number_mask(30, raster),
                        }
                        if available
                        and domain != "switch"
                        and view.get("position_known", True)
                        else {
                            "op": "mask",
                            "text": centre if available else "--",
                            "size": 30,
                        }
                    ),
                    "x": 120,
                    "y": 120,
                    "stroke": theme["primary"],
                    "colour": theme["primary"]
                    if view.get("pending")
                    else theme["text"],
                    "background": theme["bg"],
                },
                {
                    "op": "mask",
                    "x": 120,
                    "y": 143,
                    "text": "" if domain == "switch" else view.get("unit", "%"),
                    "size": 8,
                    "colour": theme["primary"],
                },
                {
                    "op": "mask",
                    "x": 120,
                    "y": 185,
                    "text": status,
                    "size": 7,
                    "colour": theme["quiet"],
                },
            ]
        )
        for index in range(19):
            angle = -126 + index * 14
            elements.append(
                line(
                    *_point(120, 118, options["gauge-radius"] - 10, angle),
                    *_point(120, 118, options["gauge-radius"] - 6, angle),
                    theme["secondary"]
                    if active and index <= round(value * 18 / 100)
                    else theme["grid"],
                )
            )
        if domain != "cover" or "stop" in view.get("actions", []):
            regions.append({"id": "control", "x": 120, "y": 120, "r": 30})
        if domain == "cover":
            for action, x in (("open", 72), ("stop", 120), ("close", 168)):
                if action not in view.get("actions", []):
                    continue
                elements.extend(
                    [
                        {"op": "circle", "x": x, "y": 211, "r": 19, "stroke": accent},
                        {
                            "op": "mask",
                            "x": x,
                            "y": 211,
                            "text": action.upper(),
                            "size": 7,
                            "colour": theme["text"],
                        },
                    ]
                )
                regions.append({"id": action, "x": x, "y": 211, "r": 19})
    else:
        if view.get("style", "NAV-ORBIT") not in {
            "NAV-ROLODEX",
            "NAV-RIBBON",
            "NAV-BREADCRUMB",
        }:
            elements.append(
                {
                    "op": "circle",
                    "x": 120,
                    "y": 109 if view.get("style") == "NAV-PETALS" else 120,
                    "r": 32
                    if view.get("style") == "NAV-PETALS"
                    else options["hub-radius"],
                    "stroke": theme["grid"],
                    "fill": theme["surface"],
                }
            )
        menu_items = [item for item in items if not item.get("settings")]
        visible, ornaments, nav_positions = navigation_layout(
            view, menu_items, selected, options, theme
        )
        elements.extend(ornaments)
        rolodex = view.get("style") == "NAV-ROLODEX"
        for index, item, x, y in visible:
            angle = index * 360 / max(1, len(menu_items))
            active = index == selected
            ink = theme["secondary"] if active else theme["text"]
            if view.get("style") != "NAV-PETALS":
                elements.extend(
                    [
                        {
                            "op": "circle",
                            "x": round(x),
                            "y": round(y),
                            "r": options["highlight-radius"] if active else 14,
                            "stroke": theme["primary"] if active else theme["quiet"],
                            "fill": theme["surface"],
                            "width": 2,
                        },
                    ]
                )
            elements.append(
                {
                    "op": "icon",
                    "x": round(x),
                    "y": round(y),
                    "icon": item.get("icon")
                    or CONTROL_TYPES.get(
                        item.get("entity_id", "").partition(".")[0],
                        (None, None, "mdi:folder"),
                    )[2],
                    "size": options["icon-size"],
                    "colour": ink,
                }
            )
            if rolodex:
                elements.append(
                    {
                        "op": "mask",
                        "x": 140,
                        "y": round(y),
                        "text": item["label"],
                        "size": 7,
                        "colour": ink,
                    }
                )
            if view.get("style") == "NAV-POINTER" and active:
                tip = _point(120, 120, options["hub-radius"] + 13, angle)
                left = _point(120, 120, options["hub-radius"], angle - 7)
                right = _point(120, 120, options["hub-radius"], angle + 7)
                elements.extend(
                    [
                        line(*tip, *left, theme["primary"]),
                        line(*left, *right, theme["primary"]),
                        line(*right, *tip, theme["primary"]),
                    ]
                )
            regions.append({"id": item["id"], "x": round(x), "y": round(y), "r": 20})
        elements.extend(
            [
                {
                    "op": "mask",
                    "x": 120,
                    "y": nav_positions["title"],
                    "text": view.get("title", "Home").upper()[:14],
                    "size": options["font-size"],
                    "colour": theme["text"],
                },
                {
                    "op": "mask",
                    "x": 120,
                    "y": nav_positions["label"] or 193,
                    "text": ""
                    if not nav_positions["label"]
                    else items[selected % len(items)]["label"]
                    if items
                    else "NO DESTINATIONS",
                    "size": 7,
                    "colour": theme["secondary"],
                },
            ]
        )

    settings_item = next((item for item in items if item.get("settings")), None)
    if settings_item:
        settings_y = nav_positions["cog"]
        active = selected == len(items) - 1
        elements.extend(
            [
                {
                    "op": "circle",
                    "x": 120,
                    "y": settings_y,
                    "r": 15,
                    "fill": theme["surface"],
                    "stroke": theme["primary"] if active else theme["quiet"],
                },
                {
                    "op": "icon",
                    "x": 120,
                    "y": settings_y,
                    "size": 18,
                    "icon": "mdi:cog",
                    "colour": theme["secondary"] if active else theme["text"],
                },
            ]
        )
        regions.append({"id": "__settings", "x": 120, "y": settings_y, "r": 17})
    footer_y = (
        212
        if extended
        else nav_positions["footer"]
        if not view.get("style", "NAV-ORBIT").startswith("CTL-")
        else 158
    )
    if not extended:
        for region in regions:
            if region["id"] in {"back", "home"}:
                region["y"] = footer_y
    for x in (90, 150):
        elements.append(
            {
                "op": "circle",
                "x": x,
                "y": footer_y,
                "r": 14,
                "stroke": theme["quiet"],
                "fill": theme["surface"],
            }
        )
    elements.extend(
        [
            line(95, footer_y, 85, footer_y, theme["primary"]),
            line(85, footer_y, 89, footer_y - 4, theme["primary"]),
            line(85, footer_y, 89, footer_y + 4, theme["primary"]),
            line(145, footer_y, 150, footer_y - 5, theme["primary"]),
            line(150, footer_y - 5, 155, footer_y, theme["primary"]),
            line(147, footer_y - 2, 147, footer_y + 5, theme["primary"]),
            line(153, footer_y - 2, 153, footer_y + 5, theme["primary"]),
            line(147, footer_y + 5, 153, footer_y + 5, theme["primary"]),
        ]
    )
    for element in elements:
        if element["op"] == "icon":
            element["background"] = (
                theme["surface"] if view.get("kind") == "menu" else theme["bg"]
            )
            element.update(
                icon_mask(
                    element.pop("icon"),
                    element.pop("size"),
                    element.pop("colour"),
                    raster,
                )
            )
        elif element["op"] == "mask":
            element.update(
                _text_mask(
                    element.pop("text"),
                    element.pop("size"),
                    element.pop("colour"),
                    raster,
                )
            )
            element["background"] = (
                theme["surface"] if view.get("kind") == "menu" else theme["bg"]
            )
    return {
        "version": 3 if any(e.get("characters") for e in elements) else 2,
        "width": 240,
        "height": 240,
        "background": theme["bg"],
        "label": view.get("title", "HA Dial"),
        "screen": view.get("id", "root"),
        "elements": elements,
        "regions": regions,
    }
