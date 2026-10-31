"""The checks that make a style real: its settings work, it looks distinct and its text fits."""

import json
from itertools import combinations

import pytest

ITEMS = [
    {"id": name.lower(), "label": name, "icon": icon, "children": []}
    for name, icon in (
        ("Building", "mdi:office-building"),
        ("Floors", "mdi:layers"),
        ("Rooms", "mdi:floor-plan"),
        ("Lights", "mdi:lightbulb"),
        ("A very long destination name", "mdi:thermometer"),
        ("Media", "mdi:play-circle"),
    )
]
CLOCK = {
    "hour": 10, "minute": 9, "second": 37, "day": 27, "date": "MON 27 OCT", "moon": "waxing_crescent",
    "reserve": 40, "zones": [("UTC", "10:09"), ("NEW YORK", "06:09"), ("TOKYO", "19:09"), ("SYDNEY", "21:09")],
    "weekday": 1, "days_in_month": 31, "weekday_name": "MONDAY", "weather": {"state": "sunny", "temperature": "17°C"},
    "sun": {"above": True, "rising": "07:18", "setting": "17:42", "progress": 0.34},
    "metrics": [
        {"label": f"Metric {n}", "value": 40 + n, "text": str(40 + n), "unit": "%", "percent": 40 + n, "series": [10, 30, 20, 50, 40]}
        for n in range(6)
    ],
}
LEVEL = {"value": 62, "continuous": True, "unit": "%", "detail": "Warm white", "state": "on", "active": True, "available": True, "icon": "mdi:lightbulb"}
SHAPES = ("INSTRUMENT", "EDITORIAL", "COLUMN", "SEGMENT", "TUMBLER")


def views(catalogue):
    for style in sorted(catalogue.NAV_STYLES):
        yield {"kind": "menu", "id": "home", "title": "Example page", "style": style, "back": True, "breadcrumbs": ["Campus", "First floor"], "items": ITEMS, "selected": 0}
    for style in sorted(catalogue.FACE_STYLES):
        yield {"kind": "menu", "id": "clock", "title": "HA DIAL", "style": style, "items": [], "back": True, "_clock": CLOCK}
    for shape in SHAPES:
        yield {"kind": "control", "id": "c", "domain": "light", "title": "Example lamp", "style": f"CTL-LIGHT-{shape}", "back": True, "actions": ["toggle", "stop"], **LEVEL}


@pytest.mark.parametrize("raster", ["smooth", "crisp"])
def test_every_declared_setting_changes_the_scene(dial, raster):
    scene, appearance = dial.load("scene"), dial.load("appearance")
    dead = []
    for view in views(dial.load("catalogue")):
        for setting in appearance.style_settings(view["style"], raster):
            if setting == "raster":
                continue
            if setting in appearance.NUMBERS:
                low, high = appearance.NUMBERS[setting][2:4]
                values = (low, high)
            elif setting in appearance.TOGGLES:
                values = (True, False)
            else:
                values = appearance.CHOICES[setting][2][:2]
            first, second = (
                scene.compile_scene({**view, "appearance": {"raster": raster, "tick-ring": True, "ring-double": True, setting: value}}) for value in values
            )
            if first == second:
                dead.append((view["style"], setting))
    assert not dead, dead


def test_settings_show_only_for_declaring_styles_and_validate(dial):
    appearance = dial.load("appearance")
    known = {*appearance.NUMBERS, *appearance.TOGGLES, *appearance.CHOICES}
    for style, settings in appearance.STYLE_SETTINGS.items():
        assert set(settings) <= known, style
    assert appearance.style_settings("CHR-TRICOMPAX") != appearance.style_settings("NAV-PETALS")
    assert "hub-radius" not in appearance.style_settings("NAV-ROLODEX")
    with pytest.raises(ValueError):
        appearance.appearance({"appearance": {"row-gap": 99}})
    with pytest.raises(ValueError):
        appearance.appearance({"appearance": {"chrome-style": "wobbly"}})


@pytest.mark.parametrize("raster", ["smooth", "crisp"])
def test_styles_for_a_domain_are_all_different(dial, raster):
    catalogue, scene = dial.load("catalogue"), dial.load("scene")
    for domain in catalogue.CONTROL_TYPES:
        styles = sorted(catalogue.control_styles(domain))
        drawings = {
            style: json.dumps(
                scene.compile_scene(
                    {"kind": "control", "id": "c", "domain": domain, "title": "Example", "style": style, "appearance": {"raster": raster}, **LEVEL}
                )["elements"]
            )
            for style in styles
        }
        for first, second in combinations(styles, 2):
            assert drawings[first] != drawings[second], (domain, first, second)
    menus = [
        json.dumps(scene.compile_scene({**view, "appearance": {"raster": raster}})["elements"])
        for view in views(catalogue)
        if view["kind"] == "menu"
    ]
    assert len(set(menus)) == len(menus)


@pytest.mark.parametrize("raster", ["smooth", "crisp"])
def test_scenes_fit_the_display_and_transport(dial, raster):
    scene = dial.load("scene")
    for view in views(dial.load("catalogue")):
        resolved = scene.compile_scene({**view, "appearance": {"raster": raster}})
        assert len(resolved["elements"]) <= 64, view["style"]
        assert len(resolved["regions"]) <= 16, view["style"]
        paired = json.dumps({"scene": resolved, "previous": resolved}, separators=(",", ":"))
        assert len(paired) <= scene.MAX_VIEW_BYTES, view["style"]
        for element in resolved["elements"]:
            if element["op"] == "mask":
                assert 0 <= element["x"] - element["width"] // 2, view["style"]
                assert element["x"] + element["width"] // 2 < 240, view["style"]


def test_crisp_never_uses_glyph_masks_and_long_text_is_elided_not_cut(dial):
    scene, canvas = dial.load("scene"), dial.load("canvas")
    for view in views(dial.load("catalogue")):
        resolved = scene.compile_scene({**view, "appearance": {"raster": "crisp"}})
        assert not any(element["op"] == "mask" for element in resolved["elements"]), view["style"]
    for crisp in (True, False):
        c = canvas.Canvas(scene.THEMES["ember"], crisp)
        value, size = c._fit("A very long destination name", 13, 1, 1, 60)
        assert c.text_size(value, size, 1, 1)[0] <= 60
        assert value.endswith("..")


def test_solid_bands_leave_no_unpainted_pixels(dial):
    """The old concentric strokes left about 14% of a thick gauge unpainted."""
    import subprocess
    from math import hypot
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    resolved = {
        "version": 5, "width": 240, "height": 240, "background": "#000000", "label": "", "screen": "", "regions": [],
        "elements": [{"op": "arc", "x": 120, "y": 120, "r": 70, "start": -180, "end": 180, "stroke": "#ffffff", "width": 10, "solid": True}],
    }
    pixels = subprocess.run(["node", "tests/scene_render.mjs"], cwd=root, input=json.dumps([resolved]).encode(), check=True, capture_output=True).stdout
    holes = sum(
        pixels[(y * 240 + x) * 4] == 0
        for y in range(240)
        for x in range(240)
        if 66 <= hypot(x - 120, y - 120) <= 73
    )
    assert holes == 0
