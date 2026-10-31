"""Feed the same resolved scenes through the real C++ parser and card raster."""

import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


FACE_CLOCK = {
    "hour": 10, "minute": 9, "second": 37, "day": 27, "weekday": 1, "days_in_month": 31, "date": "MON 27 OCT",
    "weekday_name": "MONDAY", "moon": "full_moon", "reserve": 40, "zones": [("UTC", "10:09"), ("TOKYO", "19:09")],
    "sun": {"above": True, "rising": "07:18", "setting": "17:42", "progress": 0.34},
    "weather": {"state": "rainy", "temperature": "9°C"},
    "metrics": [
        {"label": f"Example {n}", "value": 40 + n, "text": str(40 + n), "unit": "%", "percent": 40 + n, "series": [10, 30, 20, 50, 40]}
        for n in range(4)
    ],
}


def examples(scene):
    for style in (
        "AMB-SOLAR", "AMB-TYPOGRAPHIC", "AMB-ORBITAL", "AMB-STATUS", "WAT-CONTOUR", "WAT-MODULAR", "WAT-PALETTE",
        "WAT-RINGS", "WAT-SOLAR", "WAT-REFLECTIONS", "DAT-AREA", "DAT-RADAR", "DAT-BANDS", "DAT-SPARK",
    ):
        for raster in ("crisp", "smooth"):
            yield scene.compile_scene({
                "id": "face", "kind": "menu", "title": "HA DIAL", "style": style, "items": [], "back": True,
                "appearance": {"raster": raster}, "_clock": FACE_CLOCK,
            })
    for theme in scene.THEMES:
        for style in ("TRICOMPAX", "WORLDTIMER", "SKELETON", "MOONPHASE"):
            for raster in ("crisp", "smooth"):
                yield scene.compile_scene({
                    "id": "clock", "kind": "menu", "title": "HA DIAL", "theme": theme,
                    "style": f"CHR-{style}", "appearance": {"raster": raster},
                    "items": [], "_clock": {"hour": 10, "minute": 9, "second": 37,
                    "day": 27, "date": "MON 27 OCT", "moon": "waxing_crescent",
                    "zones": [("UTC", "10:09"), ("NEW YORK", "06:09"), ("TOKYO", "19:09"), ("SYDNEY", "21:09")]},
                })
    for theme in scene.THEMES:
        yield scene.compile_scene(
            {
                "kind": "menu",
                "id": "home",
                "title": "Demo home",
                "theme": theme,
                "items": [
                    {"id": "room", "label": "Demo room", "children": []},
                    {"id": "lamp", "label": "Demo lamp", "entity_id": "light.example"},
                ],
                "selected": 0,
            }
        )
        for domain, style in (
            ("light", "CTL-LIGHT-INSTRUMENT"),
            ("switch", "CTL-SWITCH-INSTRUMENT"),
            ("cover", "CTL-COVER-INSTRUMENT"),
        ):
            yield scene.compile_scene(
                {
                    "kind": "control",
                    "id": domain,
                    "title": "Demo " + domain,
                    "domain": domain,
                    "theme": theme,
                    "style": style,
                    "back": True,
                    "value": 72,
                    "active": True,
                    "available": True,
                    "actions": ["open", "stop", "close"] if domain == "cover" else [],
                }
            )

    for domain in ("light", "cover"):
        for value in (0, 9, 10, 99, 100):
            resolved = scene.compile_scene(
                {
                    "kind": "control",
                    "id": domain,
                    "domain": domain,
                    "title": "Demo " + domain,
                    "style": "CTL-LIGHT-INSTRUMENT"
                    if domain == "light"
                    else "CTL-COVER-INSTRUMENT",
                    "back": True,
                    "value": 45,
                    "active": False,
                    "available": True,
                }
            )
            yield {**resolved, "test_local_value": value}

    for style in (
        "NAV-POINTER",
        "NAV-ROLODEX",
        "NAV-PETALS",
        "NAV-CONSTELLATION",
        "NAV-COMPASS",
        "NAV-RIBBON",
        "NAV-BREADCRUMB",
        "NAV-LIST",
        "NAV-GRID",
        "NAV-PAGER",
        "NAV-NEEDLE",
    ):
        for raster in ("crisp", "smooth"):
            yield scene.compile_scene(
                {
                    "kind": "menu",
                    "id": "root",
                    "title": "Example home",
                    "style": style,
                    "selected": 8,
                    "appearance": {"raster": raster},
                    "items": [
                        *(
                            {"id": f"p{n}", "label": f"Page {n}", "icon": "mdi:folder"}
                            for n in range(8)
                        ),
                        {
                            "id": "__settings",
                            "label": "Settings",
                            "icon": "mdi:cog",
                            "settings": True,
                        },
                    ],
                }
            )
    for raster in ("crisp", "smooth"):
        for domain, base in (("light", "LIGHT"), ("climate", "THERMOSTAT"), ("select", "SELECTOR")):
            for shape in ("INSTRUMENT", "EDITORIAL", "COLUMN", "SEGMENT", "TUMBLER"):
                resolved = scene.compile_scene(
                    {
                        "kind": "control", "id": domain, "domain": domain, "title": "Example " + domain,
                        "style": f"CTL-{base}-{shape}", "icon": "mdi:lightbulb", "value": 2, "minimum": 0, "maximum": 3,
                        "step": 0.5 if domain == "climate" else 1, "available": True, "active": True, "continuous": True,
                        "state": "on", "detail": "Example status", "unit": "%", "actions": ["toggle"], "back": True,
                        "options": ["Quiet", "Normal", "Boost", "Away"] if domain == "select" else [],
                        "appearance": {"raster": raster},
                    }
                )
                yield resolved
                yield {**resolved, "test_local_value": 1}
        for name, domain, extra in (
            ("MEDIA", "media_player", {"continuous": True, "actions": ["previous", "play_pause", "next"], "detail": "Example track"}),
            ("VOLUME", "media_player", {"continuous": True}), ("COVER", "cover", {"actions": ["open", "stop", "close"]}),
            ("FAN", "fan", {"continuous": True}), ("SECURITY", "alarm_control_panel", {"state": "armed_away"}), ("LOCK", "lock", {"state": "locked"}),
            ("VACUUM", "vacuum", {"state": "cleaning", "battery": 68}), ("ENERGY", "sensor", {"numeric_value": True}), ("AIR", "sensor", {"numeric_value": True}),
            ("WEATHER", "weather", {"state": "rainy", "detail": "9° / rainy"}), ("TIMER", "timer", {"state": "active", "detail": "0:18:42"}),
            ("CALENDAR", "calendar", {"detail": "Example meeting"}), ("SCENE", "scene", {}), ("SWITCH", "switch", {"active": True}),
        ):
            yield scene.compile_scene(
                {
                    "kind": "control", "id": domain, "domain": domain, "title": "Example", "style": f"CTL-{name}-INSTRUMENT",
                    "icon": "mdi:star", "value": 42, "available": True, "active": True, "unit": "%", "back": True,
                    "state": "on", "detail": "Example", "appearance": {"raster": raster}, **extra,
                }
            )
    for domain, style, value in [
        ("climate", "THERMOSTAT", 21.5),
        ("media_player", "MEDIA", 42),
        ("sensor", "AIR", 84),
        ("lock", "LOCK", 0),
        ("select", "SELECTOR", 1),
    ]:
        for variant in ("INSTRUMENT", "EDITORIAL"):
            resolved = scene.compile_scene(
                {
                    "kind": "control",
                    "id": domain,
                    "domain": domain,
                    "title": "Example " + domain,
                    "style": f"CTL-{style}-{variant}",
                    "icon": "mdi:star",
                    "value": value,
                    "minimum": 0,
                    "maximum": 100,
                    "step": 0.5 if domain == "climate" else 1,
                    "available": True,
                    "active": True,
                    "continuous": domain in {"climate", "media_player", "select"},
                    "state": "locked" if domain == "lock" else "on",
                    "detail": "Example status",
                    "options": ["Quiet", "Normal", "Boost"]
                    if domain == "select"
                    else [],
                    "actions": ["unlock"] if domain == "lock" else [],
                    "confirmation": "unlock" if domain == "lock" else None,
                    "back": True,
                }
            )

            yield resolved
            if domain == "climate":
                for local in (-5.5, 0, 21.5, 21.6):
                    yield {**resolved, "test_local_value": local}


def test_compiler_matches_shared_fixture(dial):
    fixture = json.loads((ROOT / "tests/fixtures/scenes.json").read_text())
    assert list(examples(dial.load("scene"))) == fixture


def test_card_and_firmware_pixels_and_parser(dial, tmp_path):
    # Use the firmware's installed dependency, or an explicitly supplied include path.
    includes = Path(
        os.environ.get(
            "ARDUINOJSON_INCLUDE",
            str(
                Path.home()
                / "Library/Caches/ha-dial-build/firmware/.esphome/build/ha-dial/managed_components/bblanchon__arduinojson/src"
            ),
        )
    )
    if not (includes / "ArduinoJson.h").exists():
        pytest.skip("Build the connected firmware first, or set ARDUINOJSON_INCLUDE")
    executable = tmp_path / "scene-check"
    subprocess.run(
        [
            "c++",
            "-std=c++17",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-I",
            str(includes),
            "-I",
            str(ROOT / "tests/cpp"),
            "-I",
            str(ROOT / "components/ha_dial"),
            str(ROOT / "components/ha_dial/scene.cpp"),
            str(ROOT / "tests/scene_check.cpp"),
            "-o",
            str(executable),
        ],
        check=True,
        capture_output=True,
    )
    data = (ROOT / "tests/fixtures/scenes.json").read_bytes()
    firmware = subprocess.run(
        [str(executable)], input=data, check=True, capture_output=True
    ).stdout
    card = subprocess.run(
        ["node", "tests/scene_render.mjs"],
        cwd=ROOT,
        input=data,
        check=True,
        capture_output=True,
    ).stdout
    assert len(card) == len(json.loads(data)) * 240 * 240 * 4
    assert card == firmware
    from PIL import Image

    sheet = Image.new("RGBA", (240 * 6, 240 * 6))
    for index in range(len(json.loads(data))):
        frame = Image.frombytes(
            "RGBA", (240, 240), card[index * 230400 : (index + 1) * 230400]
        )
        sheet.paste(frame, ((index % 6) * 240, (index // 6) * 240))
    sheet.save(tmp_path / "scene-comparison.png")
