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
        assert drawing["version"] == 5
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


def _face(style, **clock):
    return {"id": "face", "kind": "menu", "title": "Home", "items": [], "style": style, "clock": clock}


def test_face_sources_read_real_state_and_missing_sources_stay_honest(integration, dial):
    clock = dial.load("chronograph")
    now = datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC)
    states = integration.hass.states
    states["sensor.level"] = SimpleNamespace(state="40", attributes={"unit_of_measurement": "%", "friendly_name": "Tank"})
    states["sensor.power"] = SimpleNamespace(state="3.5", attributes={"unit_of_measurement": "kW"})
    states["sensor.gone"] = SimpleNamespace(state="unavailable", attributes={})
    states["weather.home"] = SimpleNamespace(state="rainy", attributes={"temperature": 9.5, "temperature_unit": "°C"})
    states["sun.sun"] = SimpleNamespace(state="above_horizon", attributes={"next_rising": "2026-06-02T04:00:00+00:00", "next_setting": "2026-06-01T20:00:00+00:00"})
    resolved = clock.resolve_clock(
        integration.hass,
        _face("WAT-RINGS", weather_entity="weather.home", metrics=[
            {"entity_id": "sensor.level"}, {"entity_id": "sensor.power", "maximum": 7}, {"entity_id": "sensor.gone", "label": "Lost"}, ]),
        now,
    )["_clock"]
    first, second, third = resolved["metrics"]
    assert (first["label"], first["text"], first["unit"], first["percent"]) == ("Tank", "40", "%", 40)
    assert second["percent"] == 50
    assert (third["label"], third["text"], third["value"], third["percent"]) == ("Lost", "--", None, None)
    assert resolved["weather"] == {"state": "rainy", "temperature": "9.5°C"}
    assert resolved["sun"]["above"] and resolved["sun"]["setting"] == "20:00" and resolved["sun"]["progress"] == 0.5
    # A power reading without a maximum has no meaningful progress: rings must not invent one.
    unscaled = clock.resolve_clock(integration.hass, _face("WAT-RINGS", metrics=[{"entity_id": "sensor.power"}]), now)
    assert unscaled["_clock"]["metrics"][0]["percent"] is None
    assert clock.resolve_clock(integration.hass, _face("AMB-SOLAR"), now)["_clock"]["weather"] is None
    assert clock.source_entities(_face("AMB-SOLAR", weather_entity="weather.home")) == {"sun.sun", "weather.home"}
    assert clock.source_entities({"style": "NAV-ORBIT", "clock": {"weather_entity": "weather.home"}}) == set()
    for bad in ({"metrics": [{"entity_id": "not an entity"}]}, {"metrics": [{"entity_id": "sensor.a", "minimum": 2, "maximum": 1}]}, {"history_hours": 0}, {"weather_entity": "sensor.a"}, {"surprise": 1}):
        with pytest.raises((ValueError, TypeError)):
            clock.validate_clock(bad)


def test_only_second_showing_faces_tick_each_second(integration, dial, monkeypatch):
    runtime = dial.load("runtime")
    pushed, schedules, cancelled = [], [], []

    def schedule(hass, callback, **options):
        schedules.append((callback, options))
        return lambda: cancelled.append(callback)

    monkeypatch.setattr(runtime, "async_track_time_change", schedule)
    monkeypatch.setattr(runtime, "_push", AsyncMock(side_effect=lambda *_: pushed.append(1)))

    async def run():
        for source_style, second in (("AMB-TYPOGRAPHIC", 0), ("CHR-TRICOMPAX", "*")):
            schedules.clear()
            pushed.clear()
            definition = {"tree": {"id": "root", "title": "Home", "style": source_style, "items": []}}
            await runtime._install_definition(integration.hass, "dial", {"pages": []}, definition)
            assert schedules[-1][1] == {"second": second}
            callback = schedules[-1][0]
            await callback(SimpleNamespace(second=30))
            assert bool(pushed) == (second == "*")
            await callback(SimpleNamespace(second=0))
            assert pushed
        before = len(cancelled)
        integration.hass.data["ha_dial"]["definition_unsubs"].pop("dial")()
        assert len(cancelled) == before + 1

    asyncio.run(run())


def test_history_loads_once_updates_from_events_and_survives_no_recorder(integration, dial, monkeypatch):
    history = dial.load("history")
    hass = integration.hass
    hass.config = SimpleNamespace(components=set())
    view = _face("DAT-AREA", metrics=[{"entity_id": "sensor.level"}], history_hours=2)

    async def run():
        await history.ensure_history(hass, view)
        await history.ensure_history(hass, _face("NAV-ORBIT"))
        assert hass.data["ha_dial"]["history"] == {"sensor.level": []}
        now = dt_util_now()
        history.record_change(hass, "sensor.level", SimpleNamespace(state="not a number", last_changed=now), 2)
        assert hass.data["ha_dial"]["history"]["sensor.level"] == []
        history.record_change(hass, "sensor.level", SimpleNamespace(state="5", last_changed=now), 2)
        assert hass.data["ha_dial"]["history"]["sensor.level"][-1] == 5
        history.record_change(hass, "sensor.other", SimpleNamespace(state="5", last_changed=now), 2)
        assert "sensor.other" not in hass.data["ha_dial"]["history"]
        history.forget_history(hass)
        assert "history" not in hass.data["ha_dial"]

    def dt_util_now():
        return history.dt_util.utcnow()

    asyncio.run(run())


def test_history_reads_the_recorder_once_and_survives_its_failure(integration, dial, caplog):
    calls = []
    start_of = datetime.now(UTC)

    def changes(hass, start, *, entity_id, no_attributes):
        calls.append((entity_id, no_attributes))
        if entity_id == "sensor.broken":
            raise RuntimeError("database locked")
        return {entity_id: [SimpleNamespace(state="4", last_changed=start_of), SimpleNamespace(state="unknown", last_changed=start_of)]}

    async def executor(job):
        return job()

    dial.module(
        "homeassistant.components.recorder",
        get_instance=lambda _hass: SimpleNamespace(async_add_executor_job=executor),
        history=SimpleNamespace(state_changes_during_period=changes),
    )
    history = dial.load("history")
    hass = integration.hass
    hass.config = SimpleNamespace(components={"recorder"})
    view = _face("DAT-SPARK", metrics=[{"entity_id": "sensor.level"}, {"entity_id": "sensor.broken"}])

    async def run():
        await history.ensure_history(hass, view)
        await history.ensure_history(hass, view)

    asyncio.run(run())
    assert calls == [("sensor.level", True), ("sensor.broken", True)]
    assert hass.data["ha_dial"]["history"]["sensor.level"][-1] == 4
    assert hass.data["ha_dial"]["history"]["sensor.broken"] == []
    assert "database locked" in caplog.text
