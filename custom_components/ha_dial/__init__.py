"""HA Dial integration: HA owns navigation and sends only the current view."""

from __future__ import annotations

import asyncio
import logging
import math
from datetime import timedelta
from pathlib import Path

from homeassistant.components import frontend, websocket_api
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_FRIENDLY_NAME, CONF_ENTITY_ID
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
)

# The star keeps every command importable from here, as they were before the split.
from .commands import *
from .commands import COMMANDS, DEVICE_RE, INPUTS
from .const import CARD_URL, DEFINITIONS_KEY, DEVICE_EVENT, DOMAIN
from .deployment import manifest_version, revision
from .restart_notice import async_check_restart
from .runtime import (
    _input,
    _install_definition,
    _is_preview,
    _navigator,
    _push,
    _render_definition,
    _scene_result,
    _sync_control,
)

_LOGGER = logging.getLogger(__name__)

LOADED_VERSION = manifest_version(Path(__file__).parent)
LOADED_REVISION = revision(Path(__file__).parent)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    state = hass.data.setdefault(
        DOMAIN,
        {
            "navigators": {},
            "definitions": {},
            "definition_sources": {},
            "registered": False,
        },
    )
    state["active"] = False
    state["unloading"] = False
    if entry.title == "HA Dial":
        hass.config_entries.async_update_entry(entry, title="HA Dial Server")
    light_entity = entry.options.get(CONF_ENTITY_ID, entry.data.get(CONF_ENTITY_ID))
    light_state = hass.states.get(light_entity) if light_entity else None
    state.update(
        light_entity=light_entity,
        light_name=(
            light_state.attributes.get(ATTR_FRIENDLY_NAME) if light_state else None
        )
        or (
            light_entity.split(".", 1)[-1].replace("_", " ").title()
            if light_entity
            else "Light"
        ),
    )
    state["navigators"].clear()
    state["definitions"].clear()
    state["definition_sources"].clear()
    if not state["registered"]:
        await hass.http.async_register_static_paths(
            [
                StaticPathConfig(
                    "/ha_dial",
                    str(Path(__file__).parent / "www"),
                    False,
                )
            ]
        )
        for command in COMMANDS:
            websocket_api.async_register_command(hass, command)
        state["registered"] = True

    from .transport import watch_transports

    watch_transports(hass, entry)
    url = f"{CARD_URL}?v={LOADED_VERSION}"
    frontend.add_extra_js_url(hass, url)
    entry.async_on_unload(lambda: frontend.remove_extra_js_url(hass, url))
    from homeassistant.components import panel_custom

    await panel_custom.async_register_panel(
        hass, frontend_url_path="ha-dial", webcomponent_name="ha-dial-panel",
        sidebar_title="HA Dial", sidebar_icon="mdi:knob",
        module_url=f"/ha_dial/panel.js?v={LOADED_VERSION}", require_admin=True,
    )
    entry.async_on_unload(lambda: frontend.async_remove_panel(hass, "ha-dial"))

    def update_settings_flag(device, flag):
        if not isinstance(flag, str) or flag not in {"true", "false"}:
            return False
        enabled = flag == "true"
        policies = state.setdefault("settings_enabled", {})
        changed = policies.get(device, False) != enabled
        policies[device] = enabled
        if navigator := state["navigators"].get(device):
            navigator.settings_enabled = enabled
            if (
                not enabled
                and navigator.control
                and navigator.control.get("kind") == "settings"
            ):
                navigator.control = None
        if changed and state["active"]:
            for preview, source in state["definition_sources"].items():
                if _is_preview(preview) and source.get("preview_of") == device:
                    hass.async_create_task(
                        _push(hass, preview, _navigator(hass, preview).current())
                    )
        return changed

    @callback
    def device_input(event: Event) -> None:
        device = event.data.get("device")
        action = event.data.get("action")
        if (
            not state["active"]
            or not isinstance(device, str)
            or DEVICE_RE.fullmatch(device) is None
        ):
            return
        if not isinstance(action, str) or action not in INPUTS:
            return
        update_settings_flag(device, event.data.get("settings_enabled"))
        if device in state.get("resetting", set()) or (device in state.get("stored_definitions", {}) and state["stored_definitions"][device] is None):
            return
        if device not in state["definition_sources"] and not light_entity:
            return
        item = event.data.get("item")
        value = event.data.get("value")
        if action == "set_value":
            if not isinstance(value, (str, int, float)):
                return
            try:
                value = float(value)
            except (TypeError, ValueError):
                return
            if not math.isfinite(value):
                return
        else:
            value = None
        sequence = event.data.get("sequence")
        if sequence is not None:
            try:
                sequence = int(sequence)
            except (TypeError, ValueError):
                return
            if sequence < 0 or sequence >= 2**64:
                return
        hass.async_create_task(
            _input(
                hass,
                device,
                action,
                item if isinstance(item, str) else None,
                value,
                input_sequence=sequence,
            )
        )

    entry.async_on_unload(hass.bus.async_listen(DEVICE_EVENT, device_input))

    @callback
    def scene_status(event: Event) -> None:
        if state.get("unloading"):
            return
        device = event.data.get("device")
        try:
            received = int(event.data.get("revision", 0))
        except (TypeError, ValueError):
            return
        if not isinstance(device, str) or received != state.get("revisions", {}).get(
            device
        ):
            return
        if device in state.get("resetting", set()) or (device in state.get("stored_definitions", {}) and state["stored_definitions"][device] is None):
            return
        changed = update_settings_flag(device, event.data.get("settings_enabled"))
        if not state["active"]:
            if changed:
                state.setdefault("settings_resync", set()).add(device)
            return
        if changed:
            hass.async_create_task(
                _push(hass, device, _navigator(hass, device).current())
            )
        state.setdefault("deployment_status", {})[device] = "applied"
        async_dispatcher_send(
            hass,
            f"{DOMAIN}_scene_{device}",
            _scene_result(hass, device, _navigator(hass, device).current()),
        )

    entry.async_on_unload(
        hass.bus.async_listen("esphome.ha_dial_scene_status", scene_status)
    )

    @callback
    def frame_status(event: Event) -> None:
        device, error = event.data.get("device"), event.data.get("error", "")
        if not isinstance(device, str) or state.get("unloading"):
            return
        details = (device, event.data.get("elapsed_ms"), event.data.get("free_heap"), event.data.get("largest_block"))
        if error:
            _LOGGER.warning("Dial %s could not fetch a frame: %s (%s ms, free heap %s, largest block %s)", device, error, *details[1:])
        else:
            _LOGGER.info("Dial %s fetched a frame in %s ms (free heap %s, largest block %s)", *details)
        state.setdefault("frame_status", {})[device] = str(error)
        async_dispatcher_send(hass, f"{DOMAIN}_scene_{device}", _scene_result(hass, device, _navigator(hass, device).current()))

    entry.async_on_unload(hass.bus.async_listen("esphome.ha_dial_frame_status", frame_status))
    if "ha_dial_frame_view" not in hass.data:
        # Views can't be unregistered, so this survives reloads; it serves nothing while unloaded.
        from .frame_view import FrameView

        hass.data["ha_dial_frame_view"] = True
        hass.http.register_view(FrameView(hass))

    if light_entity:

        async def light_changed(_event: Event[EventStateChangedData]) -> None:
            for device, navigator in state["navigators"].items():
                if (
                    device in state.get("definition_sources", {})
                    or navigator.current().get("entity_id") != light_entity
                ):
                    continue
                _sync_control(hass, navigator)
                await _push(hass, device, navigator.current())

        entry.async_on_unload(
            async_track_state_change_event(hass, [light_entity], light_changed)
        )

    from homeassistant.helpers.storage import Store

    store = Store(hass, 1, DEFINITIONS_KEY)
    saved_definitions = await store.async_load() or {}
    if not isinstance(saved_definitions, dict):
        _LOGGER.error("Ignoring invalid stored HA Dial definitions")
        saved_definitions = {}
    state["definition_store"] = store
    state["stored_definitions"] = saved_definitions
    from homeassistant.exceptions import TemplateError

    for device, source in saved_definitions.items():
        if source is None:
            continue
        if (
            not isinstance(device, str)
            or DEVICE_RE.fullmatch(device) is None
            or not isinstance(source, dict)
        ):
            _LOGGER.warning("Skipping invalid saved HA Dial definition key")
            continue
        try:
            definition = _render_definition(hass, source)
            await _install_definition(hass, device, source, definition, push=True)
        except (
            TemplateError,
            AttributeError,
            KeyError,
            TypeError,
            ValueError,
        ) as error:
            _LOGGER.error(
                "Could not restore HA Dial definition for %s: %s", device, error
            )

    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))

    async def check_restart(_now=None) -> None:
        await async_check_restart(hass, LOADED_VERSION, LOADED_REVISION)

    await check_restart()
    entry.async_on_unload(
        async_track_time_interval(hass, check_restart, timedelta(seconds=30))
    )
    state["active"] = True
    for device in state.pop("settings_resync", set()):
        await _push(hass, device, _navigator(hass, device).current())
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    state = hass.data.get(DOMAIN, {})
    state["active"] = False
    state["unloading"] = True
    workers = list(state.get("scene_workers", {}).values())
    for worker in workers:
        worker.cancel()
    await asyncio.gather(*workers, return_exceptions=True)
    # Finish an in-flight save before teardown or deletion of the definitions store.
    async with state.setdefault("definition_lock", asyncio.Lock()):
        pass
    for tracker in state.get("template_trackers", {}).values():
        tracker.async_remove()
    state.get("template_trackers", {}).clear()
    for tracker in state.get("condition_trackers", {}).values():
        tracker.async_remove()
    state.get("condition_trackers", {}).clear()
    for callbacks in state.get("condition_time_unsubs", {}).values():
        for unsubscribe in callbacks:
            unsubscribe()
    state.get("condition_time_unsubs", {}).clear()
    for unsubscribe in state.get("condition_entity_unsubs", {}).values():
        unsubscribe()
    state.get("condition_entity_unsubs", {}).clear()
    for unsubscribe in state.get("definition_unsubs", {}).values():
        unsubscribe()
    state.get("definition_unsubs", {}).clear()
    for unsubscribe in state.get("explorer_unsubs", {}).values():
        unsubscribe()
    state.get("explorer_unsubs", {}).clear()
    from .transport import async_clear_views

    await async_clear_views(hass)
    return True


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    from homeassistant.helpers.storage import Store

    state = hass.data.get(DOMAIN, {})
    state["active"] = False
    state["unloading"] = True
    async with state.setdefault("definition_lock", asyncio.Lock()):
        await Store(hass, 1, DEFINITIONS_KEY).async_remove()
        state["stored_definitions"] = {}
    _LOGGER.info(
        "Removed HA Dial Server's saved definitions; dashboard cards are unchanged"
    )


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
