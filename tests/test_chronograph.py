"""Chronograph sources, navigation, scheduled updates and bounded shared scenes."""

import asyncio
import json
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest


def test_clock_validation_and_nested_definition(integration, dial):
    definition = dial.load("definition")
    for clock in (
        {"timezone": "No/Such_Zone"},
        {"world_zones": []},
        {"moon_entity": "light.example"},
        {"extra": True},
    ):
        with pytest.raises(ValueError):
            definition.build_definition(
                integration.hass,
                [{"id": "root", "title": "Time", "clock": clock}],
                "ember",
            )
    clock = {
        "timezone": "Asia/Tokyo",
        "world_zones": ["UTC", "Asia/Tokyo"],
        "moon_entity": "sensor.moon",
    }
    tree = definition.build_definition(
        integration.hass,
        [
            {"id": "root", "title": "Home"},
            {
                "id": "time",
                "parent": "root",
                "title": "Time",
                "style": "CHR-WORLDTIMER",
                "clock": clock,
            },
        ],
        "ember",
    )
    navigator = dial.load("navigator").Navigator(definition=tree)
    assert navigator.input("press")["clock"] == clock
    assert navigator.input("back")["id"] == "root"


def test_clock_sources_and_all_variants(integration, dial):
    clock = dial.load("chronograph")
    scene, protocol = dial.load("scene"), dial.load("protocol")
    now = datetime(2026, 12, 31, 23, 59, 58, tzinfo=UTC)
    integration.hass.states["sensor.moon"] = SimpleNamespace(state="full_moon")
    base = {
        "id": "time",
        "kind": "menu",
        "title": "Time",
        "items": [],
        "clock": {
            "timezone": "Asia/Tokyo",
            "moon_entity": "sensor.moon",
            "world_zones": ["UTC", "Asia/Tokyo"],
        },
    }
    drawings = []
    for style in dial.load("catalogue").CHRONOGRAPH_STYLES:
        resolved = clock.resolve_clock(integration.hass, {**base, "style": style}, now)
        assert resolved["_clock"]["day"] == 1
        assert resolved["_clock"]["hour"] == 8
        assert resolved["_clock"]["second"] == 58
        assert resolved["_clock"]["zones"] == [("UTC", "23:59"), ("TOKYO", "08:59")]
        drawing = scene.compile_scene(resolved)
        assert drawing["version"] == 4
        assert len(drawing["elements"]) <= 64
        assert len(protocol.device_payload(resolved, resolved, 1).encode()) <= 24576
        drawings.append(json.dumps(drawing))
    assert len(set(drawings)) == 4
    missing = clock.resolve_clock(
        integration.hass, {**base, "style": "CHR-MOONPHASE", "clock": {}}, now
    )
    assert missing["_clock"]["moon"] == "unavailable"
    assert "_clock" not in base


def test_clock_events_moon_changes_and_cleanup(integration, dial, monkeypatch):
    case = integration
    runtime = dial.load("runtime")
    schedules, cancelled = [], []

    def schedule(hass, callback, **options):
        schedules.append((callback, options))
        return lambda: cancelled.append(callback)

    monkeypatch.setattr(runtime, "async_track_time_change", schedule)
    monkeypatch.setattr(runtime, "_push", AsyncMock())
    source = {
        "pages": [
            {
                "id": "root",
                "title": "Time",
                "style": "CHR-MOONPHASE",
                "clock": {"moon_entity": "sensor.moon"},
            }
        ]
    }

    async def run():
        definition = runtime._render_definition(case.hass, source)
        nav = await runtime._install_definition(case.hass, "demo", source, definition)
        tick = next(
            callback for callback, options in schedules if options == {"second": "*"}
        )
        await tick(None)
        runtime._push.assert_awaited_once()
        changed = next(
            callback for entities, callback in case.watches if "sensor.moon" in entities
        )
        await changed(SimpleNamespace(data={"entity_id": "sensor.moon"}))
        assert runtime._push.await_count == 2
        nav.views[nav.view_id]["style"] = "NAV-ORBIT"
        await tick(None)
        assert runtime._push.await_count == 2
        case.data["definition_unsubs"].pop("demo")()
        assert tick in cancelled
        assert not any("sensor.moon" in entities for entities, _ in case.watches)

    asyncio.run(run())


def test_complication_availability_and_dst(integration, dial):
    clock = dial.load("chronograph")
    scene = dial.load("scene")
    view = {
        "id": "clock",
        "kind": "menu",
        "title": "Time",
        "style": "CHR-WORLDTIMER",
        "clock": {"timezone": "Europe/London", "reserve_entity": "sensor.reserve"},
    }
    for value, unit, expected in [
        ("64", "%", 64),
        ("unknown", "%", None),
        ("nan", "%", None),
        ("101", "%", None),
        ("12", "W", None),
    ]:
        integration.hass.states["sensor.reserve"] = SimpleNamespace(
            state=value, attributes={"unit_of_measurement": unit}
        )
        resolved = clock.resolve_clock(
            integration.hass, view, datetime(2026, 10, 25, 0, 30, tzinfo=UTC)
        )
        assert resolved["_clock"]["hour"] == 1
        assert resolved["_clock"]["reserve"] == expected
    repeated = clock.resolve_clock(
        integration.hass, view, datetime(2026, 10, 25, 1, 30, tzinfo=UTC)
    )
    assert repeated["_clock"]["hour"] == 1
    for phase in (
        "new_moon",
        "waxing_crescent",
        "first_quarter",
        "waxing_gibbous",
        "full_moon",
        "waning_gibbous",
        "last_quarter",
        "waning_crescent",
        "unavailable",
    ):
        integration.hass.states["sensor.moon"] = SimpleNamespace(state=phase)
        lunar = clock.resolve_clock(
            integration.hass,
            {**view, "style": "CHR-MOONPHASE", "clock": {"moon_entity": "sensor.moon"}},
            datetime(2026, 10, 25, tzinfo=UTC),
        )
        compiled = scene.compile_scene(lunar)
        assert len(compiled["elements"]) <= 64
        assert all(
            2 <= len(e["points"]) <= 128
            for e in compiled["elements"]
            if e["op"] == "polyline"
        )


def test_acknowledgement_keeps_the_published_reading(integration, dial):
    case = integration
    runtime = dial.load("runtime")
    clock = dial.load("chronograph")
    source = {"pages": [{"id": "root", "title": "Time", "style": "CHR-TRICOMPAX"}]}
    definition = runtime._render_definition(case.hass, source)

    async def run():
        navigator = await runtime._install_definition(
            case.hass, "preview_clock", source, definition
        )
        view = clock.resolve_clock(
            case.hass, navigator.current(), datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
        )
        await runtime._push(case.hass, "preview_clock", view)
        assert runtime._scene_result(case.hass, "preview_clock", navigator.current())[
            "scene"
        ] == dial.load("scene").compile_scene(view)
        case.data["definition_unsubs"].pop("preview_clock")()

    asyncio.run(run())
