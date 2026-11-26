"""HA's event loop is shared by every integration: nothing here may read the disk or rasterise on it."""

import asyncio
import builtins
import json
import sys
import threading
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

LIGHT_PAGE = {"pages": [{"id": "root", "title": "Home", "entities": ["light.example"]}]}
WORLD = {
    "id": "time", "kind": "menu", "title": "Time", "items": [], "style": "CHR-WORLDTIMER",
    "clock": {"timezone": "Asia/Tokyo", "world_zones": ["UTC", "Asia/Tokyo"]},
}


def test_after_setup_loads_resources_nothing_reads_the_disk(integration, monkeypatch):
    integration.code._load_resources()
    assets, strokes = sys.modules["dial_test.assets"], sys.modules["dial_test.strokes"]
    chronograph = sys.modules["dial_test.chronograph"]

    def refuse(*_args, **_kwargs):
        raise AssertionError("read from disk after setup")

    for owner, name in ((Path, "read_bytes"), (Path, "read_text"), (builtins, "open")):
        monkeypatch.setattr(owner, name, refuse)
    # Sizes and names no earlier test has cached, so the font really is built here.
    assert assets.icon_mask("mdi:lightbulb", 23, "#ffffff")["width"] == 23
    assert strokes.icon_paths("mdi:abacus")
    chronograph.validate_clock({"timezone": "Asia/Tokyo"})
    with pytest.raises(ValueError, match="Unknown time zone"):
        chronograph.validate_clock({"timezone": "No/Such_Zone"})


def test_scenes_compile_once_per_push_and_off_the_event_loop(integration, dial, monkeypatch):
    runtime = dial.load("runtime")
    hass = integration.hass
    compiled = []
    real = runtime.compile_scene

    def spy(view):
        compiled.append((view["id"], threading.current_thread() is threading.main_thread()))
        return real(view)

    monkeypatch.setattr(runtime, "compile_scene", spy)
    definition = runtime._render_definition(hass, LIGHT_PAGE)
    sent = []

    async def run():
        await runtime._install_definition(hass, "dial", LIGHT_PAGE, definition)
        published = []
        hass.services.async_call = AsyncMock(side_effect=lambda *args, **_: sent.append(args))
        unsubscribe = sys.modules["homeassistant.helpers.dispatcher"].async_dispatcher_connect(
            hass, "ha_dial_scene_dial", published.append
        )
        compiled.clear()
        await runtime._input(hass, "dial", "press")
        unsubscribe()
        hass.data["ha_dial"]["definition_unsubs"].pop("dial")()
        return published

    published = asyncio.run(run())
    # The opened light and the page behind it, once each: cards and the Dial share them.
    assert sorted(view for view, _ in compiled) == ["control:light.example", "root"]
    assert not any(on_loop for _, on_loop in compiled)
    payload = json.loads(sent[-1][2]["view"])
    assert payload["scene"] == published[-1]["scene"]
    assert payload["previous"]["regions"]


def test_subscribe_installs_a_definition_only_for_administrators(integration):
    integration.connection.user = SimpleNamespace(is_admin=False)
    message = {"id": 1, "device": "preview_card", "definition": LIGHT_PAGE}

    asyncio.run(integration.code._ws_subscribe(integration.hass, integration.connection, message))
    integration.connection.send_error.assert_called_once_with(1, "unauthorized", "Administrator access required")
    assert "preview_card" not in integration.data["definition_sources"]


def test_face_zones_load_in_async_code_and_a_failed_load_is_reported(integration, dial):
    clock = dial.load("chronograph")
    noon = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    resolved = asyncio.run(clock.async_resolve_clock(integration.hass, WORLD, noon))
    assert resolved["_clock"]["hour"] == 21
    assert resolved["_clock"]["zones"] == [("UTC", "12:00"), ("TOKYO", "21:00")]
    sys.modules["homeassistant.util.dt"].async_get_time_zone = AsyncMock(return_value=None)
    with pytest.raises(ValueError, match="Unknown time zone"):
        asyncio.run(clock.async_resolve_clock(integration.hass, WORLD, noon))
