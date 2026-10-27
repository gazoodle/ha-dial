"""Resynchronise scenes from ESPHome lifecycle events, without polling."""

from homeassistant.const import EVENT_SERVICE_REGISTERED
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN
from .runtime import _is_preview, _navigator, _push


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
