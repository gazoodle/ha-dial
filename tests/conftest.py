"""Isolate HA adapters while exercising the real integration and scene code."""

import asyncio
import importlib.util
import json
import sys
from enum import IntFlag
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock

import jinja2
import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def dial(monkeypatch):
    def module(name, **attributes):
        value = ModuleType(name)
        value.__dict__.update(attributes)
        monkeypatch.setitem(sys.modules, name, value)
        return value

    package = module("dial_test")
    package.__path__ = [str(ROOT / "custom_components/ha_dial")]

    def load(name):
        full_name = f"dial_test.{name}"
        spec = importlib.util.spec_from_file_location(
            full_name, package.__path__[0] + f"/{name}.py"
        )
        assert spec is not None and spec.loader is not None
        value = importlib.util.module_from_spec(spec)
        monkeypatch.setitem(sys.modules, full_name, value)
        spec.loader.exec_module(value)
        return value

    yield SimpleNamespace(load=load, module=module, package=package)
    for name in list(sys.modules):
        if name.startswith("dial_test."):
            sys.modules.pop(name, None)


@pytest.fixture
def integration(dial):
    listeners, trackers, watches = {}, [], []
    identity = lambda fn: fn
    dial.module("homeassistant")
    dial.module("homeassistant.components")
    dial.module("homeassistant.components.frontend", async_remove_panel=lambda *_: None)
    dial.module("homeassistant.components.panel_custom", async_register_panel=AsyncMock())
    dial.module(
        "homeassistant.components.websocket_api",
        websocket_command=lambda _: identity,
        async_response=identity,
    )

    class CoverEntityFeature(IntFlag):
        OPEN = 1
        CLOSE = 2
        SET_POSITION = 4
        STOP = 8

    dial.module("homeassistant.components.cover", CoverEntityFeature=CoverEntityFeature)
    dial.module("homeassistant.components.light", ATTR_BRIGHTNESS="brightness")
    dial.module("homeassistant.components.http", StaticPathConfig=SimpleNamespace)
    dial.module("homeassistant.config_entries", ConfigEntry=object)
    dial.module(
        "homeassistant.const",
        ATTR_FRIENDLY_NAME="friendly_name",
        CONF_ENTITY_ID="entity_id",
        STATE_ON="on",
        EVENT_SERVICE_REGISTERED="service_registered",
    )
    dial.module(
        "homeassistant.core",
        Event=object,
        EventStateChangedData=dict,
        HomeAssistant=object,
        State=object,
        callback=identity,
    )
    dial.module("homeassistant.helpers")

    class TemplateError(Exception):
        pass

    class HomeAssistantError(Exception):
        pass

    dial.module(
        "homeassistant.exceptions",
        TemplateError=TemplateError,
        HomeAssistantError=HomeAssistantError,
    )

    def connect(_hass, signal, callback):
        listeners.setdefault(signal, []).append(callback)
        return lambda: listeners[signal].remove(callback)

    def send(_hass, signal, payload):
        for callback in list(listeners.get(signal, [])):
            callback(payload)

    def watch(_hass, entities, callback):
        watches.append((entities, callback))
        return lambda: watches.remove((entities, callback))

    def track(_hass, templates, callback):
        tracker = SimpleNamespace(
            callback=callback, templates=templates, async_refresh=lambda: None
        )
        tracker.async_remove = lambda: trackers.remove(tracker)
        trackers.append(tracker)
        return tracker

    class Template:
        def __init__(self, source, hass):
            self.source, self.hass = source, hass

        def async_render(self, variables, parse_result=True):
            env = jinja2.Environment(loader=jinja2.DictLoader(self.hass.templates))
            result = env.from_string(self.source).render(**variables)
            return json.loads(result) if parse_result else result

    dial.module("homeassistant.helpers.template", Template=Template)
    dial.module(
        "homeassistant.helpers.dispatcher",
        async_dispatcher_connect=connect,
        async_dispatcher_send=send,
    )
    dial.module(
        "homeassistant.helpers.event",
        TrackTemplate=lambda *args: args,
        async_track_state_change_event=watch,
        async_track_template_result=track,
        async_track_time_interval=lambda *args: None,
    )
    spec = importlib.util.spec_from_file_location(
        "dial_test",
        dial.package.__path__[0] + "/__init__.py",
        submodule_search_locations=dial.package.__path__,
    )
    assert spec is not None and spec.loader is not None
    dial.package.__file__ = spec.origin
    spec.loader.exec_module(dial.package)
    data = {
        "active": True,
        "navigators": {},
        "definitions": {},
        "definition_sources": {},
        "stored_definitions": {},
        "definition_store": SimpleNamespace(async_save=AsyncMock()),
    }
    tasks = []

    def create_task(coroutine, *, eager_start=True):
        task = asyncio.Task(
            coroutine, loop=asyncio.get_running_loop(), eager_start=eager_start
        )
        tasks.append(task)
        return task

    hass = SimpleNamespace(
        data={"ha_dial": data},
        states={
            "light.example": SimpleNamespace(
                state="on",
                attributes={"brightness": 128, "friendly_name": "Demo light"},
            )
        },
        services=SimpleNamespace(
            has_service=lambda domain, _: domain == "esphome", async_call=AsyncMock()
        ),
        templates={},
        async_create_task=create_task,
    )
    connection = SimpleNamespace(
        send_result=AsyncMock(),
        send_error=AsyncMock(),
        send_event=lambda *args: None,
        subscriptions={},
        user=SimpleNamespace(is_admin=True),
    )
    # HA sends these messages synchronously, so record calls without awaiting.
    from unittest.mock import Mock

    connection.send_result, connection.send_error = Mock(), Mock()
    return SimpleNamespace(
        code=dial.package,
        hass=hass,
        data=data,
        connection=connection,
        trackers=trackers,
        watches=watches,
        tasks=tasks,
    )
