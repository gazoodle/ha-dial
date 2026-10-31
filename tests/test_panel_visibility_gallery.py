"""Time visibility transitions and authoritative gallery scenes."""

import asyncio
import sys
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

from jinja2.nativetypes import NativeEnvironment


def test_condition_template_endpoint_validates_and_requires_admin(integration):
    case = integration

    async def run():
        await case.code._ws_condition_template(case.hass, case.connection, {"id": 1, "condition": {"condition": "state", "entity_id": "select.example", "state": "Home"}})
        assert "select.example" in case.connection.send_result.call_args.args[1]
        await case.code._ws_condition_template(case.hass, case.connection, {"id": 2, "condition": {"condition": "state"}})
        assert case.connection.send_error.call_args.args[1] == "invalid_condition"
        case.connection.user.is_admin = False
        await case.code._ws_condition_template(case.hass, case.connection, {"id": 3, "condition": {"condition": "state"}})
        assert case.connection.send_error.call_args.args[1] == "unauthorized"

    asyncio.run(run())


def test_state_condition_watches_hidden_page_and_updates(integration, dial, monkeypatch):
    case = integration
    env = NativeEnvironment()
    env.globals["states"] = lambda entity: case.hass.states[entity].state

    class Template:
        def __init__(self, source, hass):
            self.source = source

        def async_render(self, variables=None, parse_result=True):
            return env.from_string(self.source).render(**(variables or {}))

    dial.module("homeassistant.helpers.template", Template=Template)
    runtime = sys.modules[case.code._install_definition.__module__]
    monkeypatch.setattr(runtime, "_push", AsyncMock())
    case.hass.states["select.example"] = SimpleNamespace(state="Away", attributes={})
    source = {"pages": [
        {"id": "home", "title": "Home"},
        {"id": "room", "title": "Room", "parent": "home", "conditions": [
            {"condition": "state", "entity_id": "select.example", "state": "Home"}
        ]},
    ]}

    async def run():
        await case.code._ws_configure(case.hass, case.connection, {"id": 1, "device": "demo", "definition": source})
        assert case.data["definitions"]["demo"]["tree"]["items"] == []
        callback = next(callback for entities, callback in case.watches if "select.example" in entities)
        case.hass.states["select.example"].state = "Home"
        callback(None)
        assert case.data["definitions"]["demo"]["tree"]["items"][0]["id"] == "room"
        case.hass.states["select.example"].state = "Away"
        callback(None)
        assert case.data["definitions"]["demo"]["tree"]["items"] == []
        await asyncio.gather(*case.tasks)

    asyncio.run(run())


def test_time_visibility_changes_at_scheduled_boundaries(integration, dial, monkeypatch):
    case = integration
    now = [datetime(2026, 10, 30, 21, 59, 59)]
    env = NativeEnvironment()
    env.globals["now"] = lambda: now[0]

    class Template:
        def __init__(self, source, hass):
            self.source = source

        def async_render(self, variables=None, parse_result=True):
            return env.from_string(self.source).render(**(variables or {}))

    dial.module("homeassistant.helpers.template", Template=Template)
    runtime = dial.load("runtime")
    schedules = {}
    cancelled = []

    def schedule(hass, callback, **time):
        key = tuple(time.values())
        schedules[key] = callback
        return lambda: cancelled.append(key)

    monkeypatch.setattr(runtime, "async_track_time_change", schedule)
    monkeypatch.setattr(runtime, "_push", AsyncMock())
    source = {"pages": [{"id": "home", "title": "Home", "entities": [{"entity_id": "light.example", "conditions": [{"condition": "time", "after": "22:00:00", "before": "06:00:00", "weekday": ["fri", "sat"]}]}]}]}

    async def run():
        definition = runtime._render_definition(case.hass, source)
        assert definition["tree"]["items"] == []
        await runtime._install_definition(case.hass, "demo", source, definition)
        assert set(schedules) == {(0, 0, 0), (22, 0, 0), (6, 0, 0)}
        now[0] = datetime(2026, 10, 30, 22, 0, 0)
        schedules[(22, 0, 0)](now[0])
        assert len(case.data["definitions"]["demo"]["tree"]["items"]) == 1
        now[0] = datetime(2026, 10, 31, 6, 0, 0)
        schedules[(6, 0, 0)](now[0])
        assert case.data["definitions"]["demo"]["tree"]["items"] == []
        await runtime._install_definition(case.hass, "demo", source, definition)
        assert len(cancelled) == 3
        await asyncio.gather(*case.tasks)

    asyncio.run(run())


def test_gallery_uses_domain_styles_and_real_scene(integration):
    async def run():
        await integration.code._ws_gallery(integration.hass, integration.connection, {
            "id": 1, "page": {"title": "Home", "entities": ["light.example"]},
            "entity": "light.example", "theme": "ember",
        })
        result = integration.connection.send_result.call_args.args[1]
        assert set(result["styles"]) == {f"CTL-LIGHT-{shape}" for shape in ("INSTRUMENT", "EDITORIAL", "COLUMN", "SEGMENT", "TUMBLER")}
        assert len(result["themes"]) == 6
        assert all(scene["elements"] for scene in result["styles"].values())
        await integration.code._ws_gallery(integration.hass, integration.connection, {
            "id": 2, "page": {"title": "Home"}, "theme": "ember",
        })
        navigation = integration.connection.send_result.call_args.args[1]
        assert len(navigation["styles"]) == 34
        assert len(navigation["styles"]["NAV-ORBIT"]["regions"]) >= 4
        await integration.code._ws_gallery(integration.hass, integration.connection, {
            "id": 3, "page": {"title": "Home", "appearance": {"background": "#123456"}},
            "theme": "ember", "preview_only": True,
        })
        preview = integration.connection.send_result.call_args.args[1]
        assert set(preview) == {"scene", "frames"}
        assert preview["scene"]["background"].lower() == "#123456"
        assert not any(region["id"].startswith("gallery_") for region in preview["scene"]["regions"])

    asyncio.run(run())
