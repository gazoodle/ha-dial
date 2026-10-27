"""Compile a saved Dial definition and current navigation state into a scene."""

from __future__ import annotations

from math import cos, pi, sin

from .assets import _number_mask, _text_mask

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
    items = view.get("items", [])[:8]
    selected = view.get("selected", 0)
    elements = [
        {
            "op": "circle",
            "x": 120,
            "y": 120,
            "r": 116,
            "stroke": theme["primary"],
            "width": 2,
        }
    ]
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

    if view.get("style", "NAV-ORBIT").startswith("CTL-"):
        domain = view.get("domain", "light")
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
                    "r": 70,
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
                    "r": 70,
                    "start": -132,
                    "end": 132,
                    "value": round(value),
                    "stroke": accent,
                    "width": 6,
                },
                {
                    **(
                        {"op": "number", "value": round(value), **_number_mask(30)}
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
                    *_point(120, 118, 60, angle),
                    *_point(120, 118, 64, angle),
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
        elements.append(
            {
                "op": "circle",
                "x": 120,
                "y": 120,
                "r": 55,
                "stroke": theme["grid"],
                "fill": theme["surface"],
            }
        )
        for index, item in enumerate(items):
            angle = index * 360 / max(1, len(items))
            x, y = _point(120, 120, 84, angle)
            active = index == selected
            ink = theme["secondary"] if active else theme["text"]
            elements.extend(
                [
                    {
                        "op": "circle",
                        "x": round(x),
                        "y": round(y),
                        "r": 18 if active else 14,
                        "stroke": theme["primary"] if active else theme["quiet"],
                        "fill": theme["surface"],
                        "width": 2,
                    },
                ]
            )
            domain = item.get("entity_id", "").partition(".")[0]
            if domain == "switch":
                elements.extend(
                    [
                        {
                            "op": "circle",
                            "x": round(x),
                            "y": round(y),
                            "r": 7,
                            "stroke": ink,
                        },
                        line(x, y - 9, x, y, ink),
                    ]
                )
            elif domain == "cover":
                elements.extend(
                    [
                        line(x - 6, y - 6, x + 6, y - 6, ink),
                        line(x - 6, y, x + 6, y, ink),
                        line(x - 6, y + 6, x + 6, y + 6, ink),
                    ]
                )
            elif domain == "light":
                elements.extend(
                    [
                        {
                            "op": "circle",
                            "x": round(x),
                            "y": round(y - 2),
                            "r": 4,
                            "stroke": ink,
                        },
                        line(x - 3, y + 3, x + 3, y + 3, ink),
                        line(x - 2, y + 6, x + 2, y + 6, ink),
                    ]
                )
            else:
                elements.extend(
                    [
                        line(x - 6, y - 5, x + 6, y - 5, ink),
                        line(x + 6, y - 5, x + 6, y + 5, ink),
                        line(x + 6, y + 5, x - 6, y + 5, ink),
                        line(x - 6, y + 5, x - 6, y - 5, ink),
                        line(x, y - 5, x, y + 5, ink),
                    ]
                )
            regions.append({"id": item["id"], "x": round(x), "y": round(y), "r": 22})
        elements.extend(
            [
                {
                    "op": "mask",
                    "x": 120,
                    "y": 108,
                    "text": view.get("title", "Home").upper()[:14],
                    "size": 11,
                    "colour": theme["text"],
                },
                {
                    "op": "mask",
                    "x": 120,
                    "y": 128,
                    "text": items[selected % len(items)]["label"]
                    if items
                    else "NO DESTINATIONS",
                    "size": 7,
                    "colour": theme["secondary"],
                },
            ]
        )

    for x in (90, 150):
        elements.append(
            {
                "op": "circle",
                "x": x,
                "y": 158,
                "r": 14,
                "stroke": theme["quiet"],
                "fill": theme["surface"],
            }
        )
    elements.extend(
        [
            line(95, 158, 85, 158, theme["primary"]),
            line(85, 158, 89, 154, theme["primary"]),
            line(85, 158, 89, 162, theme["primary"]),
            line(145, 158, 150, 153, theme["primary"]),
            line(150, 153, 155, 158, theme["primary"]),
            line(147, 156, 147, 163, theme["primary"]),
            line(153, 156, 153, 163, theme["primary"]),
            line(147, 163, 153, 163, theme["primary"]),
        ]
    )
    for element in elements:
        if element["op"] == "mask":
            element.update(
                _text_mask(
                    element.pop("text"), element.pop("size"), element.pop("colour")
                )
            )
            element["background"] = (
                theme["surface"] if view.get("kind") == "menu" else theme["bg"]
            )
    return {
        "version": 2,
        "width": 240,
        "height": 240,
        "background": theme["bg"],
        "label": view.get("title", "HA Dial"),
        "screen": view.get("id", "root"),
        "elements": elements,
        "regions": regions,
    }
