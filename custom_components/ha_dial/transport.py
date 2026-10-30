"""Resynchronise scenes from ESPHome lifecycle events, without polling."""

import asyncio
import json
import logging

from homeassistant.const import EVENT_SERVICE_REGISTERED
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import DOMAIN
from .runtime import _is_preview, _navigator, _next_revision, _push

_LOGGER = logging.getLogger(__name__)


async def async_clear_view(hass: HomeAssistant, device: str) -> bool:
    if _is_preview(device):
        return False
    message = "HA Dial Server is restarting or has been removed" if hass.data[DOMAIN].get("unloading") else "Dial has no active configuration"
    async_dispatcher_send(hass, f"{DOMAIN}_scene_{device}", {"error": message})
    service = f"{device}_ha_dial_show_view"
    if not hass.services.has_service("esphome", service) or not hass.data[DOMAIN].get("transport_available", {}).get(device, True):
        return False
    try:
        async with asyncio.timeout(2):
            await hass.services.async_call(
                "esphome", service,
                {"view": json.dumps({"revision": _next_revision(hass, device), "clear": True})},
                blocking=True,
            )
        return True
    except (HomeAssistantError, TimeoutError) as error:
        _LOGGER.warning("Could not clear HA Dial display for %s: %s", device, error)
        return False


async def async_clear_views(hass: HomeAssistant) -> None:
    await asyncio.gather(
        *(async_clear_view(hass, device) for device in hass.data[DOMAIN].get("navigators", {}))
    )


def watch_transports(hass: HomeAssistant, owner) -> None:
    state = hass.data[DOMAIN]
    availability = state.setdefault("transport_available", {})
    bindings = {}
    entries = {}

    def bind(entry):
        runtime = getattr(entry, "runtime_data", None)
        previous = bindings.get(entry.entry_id)
        if previous and previous[0] is runtime:
            return
        if previous:
            previous[1]()
            bindings.pop(entry.entry_id)
        if runtime is None:
            return

        @callback
        def changed():
            info = runtime.device_info
            if info is None:
                return
            device = info.name.replace("-", "_")
            available = runtime.available
            previous_available = availability.get(device)
            availability[device] = available
            if (
                device in state["definition_sources"]
                and available != previous_available
            ):
                hass.async_create_task(
                    _push(hass, device, _navigator(hass, device).current())
                )

        bindings[entry.entry_id] = (
            runtime,
            runtime.async_subscribe_device_updated(changed),
        )
        changed()

    @callback
    def registered(event=None):
        for entry in hass.config_entries.async_entries("esphome"):
            if entry.entry_id not in entries:
                entries[entry.entry_id] = entry.async_on_state_change(
                    lambda entry=entry: bind(entry)
                )
            bind(entry)
        if event is None or event.data.get("domain") != "esphome":
            return
        service = event.data.get("service", "")
        suffix = "_ha_dial_show_view"
        if not service.endswith(suffix):
            return
        device = service[: -len(suffix)]
        if not _is_preview(device) and device in state["definition_sources"]:
            hass.async_create_task(
                _push(hass, device, _navigator(hass, device).current())
            )

    @callback
    def cleanup():
        for _runtime, unsubscribe in bindings.values():
            unsubscribe()
        for unsubscribe in entries.values():
            unsubscribe()
        bindings.clear()
        entries.clear()

    owner.async_on_unload(cleanup)
    owner.async_on_unload(hass.bus.async_listen(EVENT_SERVICE_REGISTERED, registered))
    registered()
