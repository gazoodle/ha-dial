"""Feed the same resolved scenes through the real C++ parser and card raster."""

import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def examples(scene):
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
