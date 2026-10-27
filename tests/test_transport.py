"""Exercise reconnect resends with the ESPHome lifecycle callback contract."""

import asyncio
import importlib
from types import SimpleNamespace

from test_integration import SOURCE


def test_reconnect_and_service_registration_resend_without_polling(integration):
    async def run():
        i = integration
        await i.code._ws_configure(
            i.hass, i.connection, {"id": 1, "device": "demo_dial", "definition": SOURCE}
        )
        transport = importlib.import_module("dial_test.transport")
        updates, state_changes, cleanup, listeners = [], [], [], {}
        runtime = SimpleNamespace(
            available=False, device_info=SimpleNamespace(name="demo-dial")
        )

        def subscribe(callback):
            updates.append(callback)
            return lambda: updates.remove(callback)

        def state_change(callback):
            state_changes.append(callback)
            return lambda: state_changes.remove(callback)

        def listen(event, callback):
            listeners[event] = callback
            return lambda: listeners.pop(event)

        runtime.async_subscribe_device_updated = subscribe
        entry = SimpleNamespace(
            entry_id="example", runtime_data=runtime, async_on_state_change=state_change
        )
        i.hass.config_entries = SimpleNamespace(async_entries=lambda domain: [entry])
        i.hass.bus = SimpleNamespace(async_listen=listen)
        transport.watch_transports(
            i.hass, SimpleNamespace(async_on_unload=cleanup.append)
        )
        await asyncio.gather(*i.tasks)
        assert i.data["deployment_status"]["demo_dial"] == "waiting"
        i.hass.services.async_call.reset_mock()
        runtime.available = True
        updates[0]()
        await asyncio.gather(*i.tasks)
        assert i.hass.services.async_call.await_count == 1
        assert i.data["deployment_status"]["demo_dial"] == "sent"
        updates[0]()
        await asyncio.gather(*i.tasks)
        assert i.hass.services.async_call.await_count == 1, (
            "ordinary metadata updates must not resend"
        )
        listeners["service_registered"](
            SimpleNamespace(
                data={"domain": "esphome", "service": "demo_dial_ha_dial_show_view"}
            )
        )
        await asyncio.gather(*i.tasks)
        assert i.hass.services.async_call.await_count == 2
        runtime.available = False
        updates[0]()
        await asyncio.gather(*i.tasks)
        assert i.data["deployment_status"]["demo_dial"] == "waiting"
        for callback in cleanup:
            callback()
        assert not listeners and not updates and not state_changes

    asyncio.run(run())


def test_unchanged_saved_card_mount_resynchronises_without_resetting_navigation(
    integration,
):
    async def run():
        i = integration
        message = {"id": 1, "device": "demo_dial", "definition": SOURCE}
        await i.code._ws_configure(i.hass, i.connection, message)
        await i.code._input(i.hass, "demo_dial", "press")
        page = i.code._navigator(i.hass, "demo_dial").view_id
        i.hass.services.async_call.reset_mock()
        await i.code._ws_configure(i.hass, i.connection, message)
        assert i.code._navigator(i.hass, "demo_dial").view_id == page
        i.hass.services.async_call.assert_awaited_once()
        assert i.data["definition_store"].async_save.await_count == 1

    asyncio.run(run())
