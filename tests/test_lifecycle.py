"""Saved screens survive reloads, but not removal of HA Dial Server."""

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from test_integration import SOURCE


@pytest.fixture
def lifecycle(integration, dial, tmp_path):
    i = integration
    saved = tmp_path / "definitions.json"

    class Store:
        def __init__(self, hass, version, key):
            assert key == "ha_dial_definitions"

        async def async_load(self):
            return json.loads(saved.read_text()) if saved.exists() else None

        async def async_save(self, value):
            saved.write_text(json.dumps(value))

        async def async_remove(self):
            saved.unlink(missing_ok=True)

    dial.module("homeassistant.helpers.storage", Store=Store)
    i.data["registered"] = False
    i.hass.http = SimpleNamespace(async_register_static_paths=AsyncMock(), register_view=lambda _view: None)
    i.code.StaticPathConfig = lambda *args: args
    i.code.frontend.add_extra_js_url = Mock()
    i.code.frontend.remove_extra_js_url = Mock()
    i.code.websocket_api.async_register_command = Mock()
    i.code.async_check_restart = AsyncMock()
    listeners = {}

    def listen(event, callback):
        listeners.setdefault(event, []).append(callback)
        return lambda: listeners[event].remove(callback)

    i.hass.bus = SimpleNamespace(async_listen=listen)
    i.hass.config_entries = SimpleNamespace(
        async_entries=lambda domain: [], async_update_entry=Mock()
    )
    cleanup = []
    entry = SimpleNamespace(
        title="HA Dial",
        data={},
        options={},
        async_on_unload=cleanup.append,
        add_update_listener=lambda callback: Mock(),
    )
    return SimpleNamespace(
        i=i, entry=entry, saved=saved, cleanup=cleanup, listeners=listeners
    )


def test_unconfigured_dial_stays_in_onboarding(lifecycle):
    async def run():
        case = lifecycle
        i = case.i
        assert await i.code.async_setup_entry(i.hass, case.entry)
        for action in ("ready", "press", "rotate_right"):
            case.listeners["esphome.ha_dial_input"][0](
                SimpleNamespace(data={"device": "demo_dial", "action": action})
            )
        await asyncio.gather(*i.tasks)
        assert not i.data["navigators"], (
            "no placeholder screen before a card supplies a definition"
        )
        i.hass.services.async_call.assert_not_called()
        await i.code._ws_configure(
            i.hass, i.connection, {"id": 1, "device": "demo_dial", "definition": SOURCE}
        )
        i.hass.services.async_call.reset_mock()
        case.listeners["esphome.ha_dial_input"][0](
            SimpleNamespace(data={"device": "demo_dial", "action": "ready"})
        )
        await asyncio.gather(*i.tasks)
        i.hass.services.async_call.assert_awaited_once()

    asyncio.run(run())


def test_reset_marker_survives_restart_with_legacy_light(lifecycle):
    async def run():
        case = lifecycle
        case.saved.write_text(json.dumps({"demo_dial": None}))
        case.entry.data = {"entity_id": "light.example"}
        assert await case.i.code.async_setup_entry(case.i.hass, case.entry)
        case.listeners["esphome.ha_dial_input"][0](SimpleNamespace(data={"device": "demo_dial", "action": "ready"}))
        await asyncio.gather(*case.i.tasks)
        assert "demo_dial" not in case.i.data["navigators"]
        case.i.hass.services.async_call.assert_not_called()

    asyncio.run(run())


def test_custom_server_title_is_preserved(lifecycle):
    async def run():
        case = lifecycle
        case.entry.title = "Demo controllers"
        assert await case.i.code.async_setup_entry(case.i.hass, case.entry)
        case.i.hass.config_entries.async_update_entry.assert_not_called()

    asyncio.run(run())


def test_unload_clears_live_screens_and_blocks_late_input(lifecycle):
    async def run():
        case = lifecycle
        i = case.i
        assert await i.code.async_setup_entry(i.hass, case.entry)
        await i.code._ws_configure(
            i.hass, i.connection, {"id": 1, "device": "demo_dial", "definition": SOURCE}
        )
        await i.code._input(i.hass, "demo_dial", "press")
        await i.code._input(i.hass, "demo_dial", "press")
        events = []
        i.connection.send_event = lambda _, value: events.append(value)
        await i.code._ws_subscribe(
            i.hass, i.connection, {"id": 2, "device": "demo_dial"}
        )
        old_revision = i.data["revisions"]["demo_dial"]
        await i.code.async_unload_entry(i.hass, case.entry)
        clear = json.loads(i.hass.services.async_call.call_args.args[2]["view"])
        assert clear["clear"] is True and clear["revision"] > old_revision
        assert "restarting or has been removed" in events[-1]["error"]
        count = len(events)
        case.listeners["esphome.ha_dial_scene_status"][0](
            SimpleNamespace(data={"device": "demo_dial", "revision": clear["revision"]})
        )
        assert len(events) == count, (
            "clear acknowledgement must not restore an applied claim"
        )
        i.hass.services.async_call.reset_mock()
        await i.code._input(i.hass, "demo_dial", "set_value", value=42)
        await i.code._push(
            i.hass, "demo_dial", i.code._navigator(i.hass, "demo_dial").current()
        )
        i.hass.services.async_call.assert_not_called()

    asyncio.run(run())


def test_reload_restores_but_removal_requires_a_saved_card_to_restore(lifecycle):
    async def run():
        case = lifecycle
        i = case.i
        case.saved.write_text(json.dumps({"demo_dial": SOURCE}))
        assert await i.code.async_setup_entry(i.hass, case.entry)
        assert i.data["definition_sources"]["demo_dial"] == SOURCE
        i.hass.config_entries.async_update_entry.assert_called_with(
            case.entry, title="HA Dial Server"
        )

        assert await i.code.async_unload_entry(i.hass, case.entry)
        assert case.saved.exists(), "ordinary reload must retain saved definitions"
        for callback in case.cleanup:
            if callback is not None:
                callback()
        case.cleanup.clear()
        assert await i.code.async_setup_entry(i.hass, case.entry)
        assert i.data["definition_sources"]["demo_dial"] == SOURCE

        assert await i.code.async_unload_entry(i.hass, case.entry)
        await i.code.async_remove_entry(i.hass, case.entry)
        assert not case.saved.exists()
        message = {"id": 1, "device": "demo_dial", "definition": SOURCE}
        await i.code._ws_configure(i.hass, i.connection, message)
        assert i.connection.send_error.call_args.args[1] == "not_loaded"
        assert not case.saved.exists(), "an open card must not recreate removed storage"

        i.hass.services.async_call.reset_mock()
        assert await i.code.async_setup_entry(i.hass, case.entry)
        assert not i.data["definition_sources"]
        i.hass.services.async_call.assert_not_called()
        await i.code._ws_configure(i.hass, i.connection, message)
        assert json.loads(case.saved.read_text()) == {"demo_dial": SOURCE}

    asyncio.run(run())


def test_unload_reports_unreachable_display(lifecycle, caplog):
    async def run():
        from homeassistant.exceptions import HomeAssistantError

        case = lifecycle
        i = case.i
        assert await i.code.async_setup_entry(i.hass, case.entry)
        await i.code._ws_configure(
            i.hass, i.connection, {"id": 1, "device": "demo_dial", "definition": SOURCE}
        )
        i.hass.services.async_call.side_effect = HomeAssistantError(
            "Demo device disconnected"
        )
        assert await i.code.async_unload_entry(i.hass, case.entry)
        assert "Could not clear HA Dial display" in caplog.text
        assert "Demo device disconnected" in caplog.text
        assert case.saved.exists(), (
            "failed display delivery must not erase saved configuration"
        )

    asyncio.run(run())


def test_unloaded_server_rejects_all_card_commands(integration):
    async def run():
        i = integration
        i.data["active"] = False
        for handler in (
            i.code._ws_view,
            i.code._ws_input,
            i.code._ws_configure,
            i.code._ws_subscribe,
        ):
            await handler(i.hass, i.connection, {"id": 1, "device": "demo_dial"})
            assert i.connection.send_error.call_args.args[1] == "not_loaded"
        assert not i.data["navigators"]
        i.hass.services.async_call.assert_not_called()
        i.data["definition_store"].async_save.assert_not_called()

    asyncio.run(run())


def test_removal_waits_for_save_and_rejects_queued_saves(lifecycle):
    async def run():
        case = lifecycle
        i = case.i
        assert await i.code.async_setup_entry(i.hass, case.entry)
        saving, release = asyncio.Event(), asyncio.Event()
        original_save = i.data["definition_store"].async_save

        async def save(value):
            saving.set()
            await release.wait()
            await original_save(value)

        i.data["definition_store"].async_save = save
        message = {"id": 1, "device": "demo_dial", "definition": SOURCE}
        first = asyncio.create_task(i.code._ws_configure(i.hass, i.connection, message))
        await saving.wait()
        queued = asyncio.create_task(
            i.code._ws_configure(
                i.hass, i.connection, {**message, "device": "other_dial"}
            )
        )
        unload = asyncio.create_task(i.code.async_unload_entry(i.hass, case.entry))
        release.set()
        await asyncio.wait_for(asyncio.gather(first, queued, unload), timeout=1)
        await i.code.async_remove_entry(i.hass, case.entry)
        assert not case.saved.exists()
        assert i.connection.send_error.call_args.args[1] == "not_loaded"
        assert not i.data.get("scene_workers")

    asyncio.run(run())
