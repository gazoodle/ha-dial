"""HA Dial integration: HA owns navigation and sends only the current view."""

from __future__ import annotations

import asyncio
import logging
import math
import re
from datetime import timedelta
from functools import wraps
from pathlib import Path

import voluptuous as vol
from homeassistant.components import frontend, websocket_api
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_FRIENDLY_NAME, CONF_ENTITY_ID
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError, TemplateError
from homeassistant.helpers.dispatcher import (
    async_dispatcher_connect,
    async_dispatcher_send,
)
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
)

from .const import CARD_URL, DEFINITIONS_KEY, DEVICE_EVENT, DOMAIN
from .deployment import manifest_version, revision
from .navigator import Navigator
from .protocol import device_payload
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
INPUTS = {
    "ready",
    "rotate_left",
    "rotate_right",
    "set_value",
    "press",
    "touch",
    "back",
    "home",
}
DEVICE_RE = re.compile(r"^[a-z0-9_]{1,64}$")
DEVICE_SCHEMA = vol.All(str, vol.Match(DEVICE_RE))


def _require_server(handler):
    @wraps(handler)
    async def checked(hass, connection, msg):
        if not hass.data.get(DOMAIN, {}).get("active"):
            connection.send_error(
                msg["id"],
                "not_loaded",
                "Add HA Dial Server in Settings / Devices & services first",
            )
            return
        await handler(hass, connection, msg)

    return checked


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
        websocket_api.async_register_command(hass, _ws_view)
        websocket_api.async_register_command(hass, _ws_input)
        websocket_api.async_register_command(hass, _ws_configure)
        websocket_api.async_register_command(hass, _ws_subscribe)
        websocket_api.async_register_command(hass, _ws_definitions)
        websocket_api.async_register_command(hass, _ws_gallery)
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
    for unsubscribe in state.get("definition_unsubs", {}).values():
        unsubscribe()
    state.get("definition_unsubs", {}).clear()
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


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/view",
        vol.Optional("device", default="preview"): DEVICE_SCHEMA,
    }
)
@websocket_api.async_response
@_require_server
async def _ws_view(hass, connection, msg) -> None:
    connection.send_result(
        msg["id"],
        _scene_result(hass, msg["device"], _navigator(hass, msg["device"]).current()),
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/input",
        vol.Optional("device", default="preview"): DEVICE_SCHEMA,
        vol.Required("action"): vol.In(INPUTS),
        vol.Optional("item"): str,
        vol.Optional("value"): vol.Coerce(float),
    }
)
@websocket_api.async_response
@_require_server
async def _ws_input(hass, connection, msg) -> None:
    if msg.get("value") is not None and not math.isfinite(msg["value"]):
        connection.send_error(msg["id"], "invalid_format", "Value must be finite")
        return
    try:
        view = await _input(
            hass, msg["device"], msg["action"], msg.get("item"), msg.get("value")
        )
    except HomeAssistantError as error:
        _sync_control(hass, _navigator(hass, msg["device"]))
        await _push(hass, msg["device"], _navigator(hass, msg["device"]).current())
        connection.send_error(msg["id"], "service_error", str(error))
        return
    connection.send_result(msg["id"], _scene_result(hass, msg["device"], view))


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/configure",
        vol.Required("device"): DEVICE_SCHEMA,
        vol.Required("definition"): dict,
    }
)
@websocket_api.async_response
@_require_server
async def _ws_configure(hass, connection, msg) -> None:
    if not connection.user or not connection.user.is_admin:
        connection.send_error(msg["id"], "unauthorized", "Administrator access required")
        return
    source = msg["definition"]
    device = msg["device"]
    if not isinstance(source.get("template", ""), str) or not isinstance(
        source.get("theme", "ember"), str
    ):
        connection.send_error(
            msg["id"], "invalid_format", "Template and theme must be text"
        )
        return
    from homeassistant.exceptions import TemplateError

    try:
        definition = _render_definition(hass, source)
    except TemplateError as error:
        connection.send_error(msg["id"], "template_error", str(error))
        return
    except (AttributeError, KeyError, TypeError, ValueError) as error:
        connection.send_error(msg["id"], "invalid_format", str(error))
        return

    state = hass.data[DOMAIN]
    if source == state["definition_sources"].get(device):
        if not _is_preview(device):
            _sync_control(hass, _navigator(hass, device))
            await _push(hass, device, _navigator(hass, device).current())
        connection.send_result(
            msg["id"], _scene_result(hass, device, _navigator(hass, device).current())
        )
        return
    candidate = Navigator(definition=definition)
    device_payload(candidate.current(), None, 0)
    if not _is_preview(device):
        async with state.setdefault("definition_lock", asyncio.Lock()):
            if not state["active"]:
                connection.send_error(
                    msg["id"], "not_loaded", "HA Dial Server was unloaded"
                )
                return
            stored = {**state.get("stored_definitions", {}), device: source}
            await state["definition_store"].async_save(stored)
            state["stored_definitions"] = stored
            if not state["active"]:
                connection.send_error(
                    msg["id"], "not_loaded", "HA Dial Server was unloaded"
                )
                return
            navigator = await _install_definition(
                hass, device, source, definition, push=True
            )
    else:
        navigator = await _install_definition(
            hass, device, source, definition, push=True
        )
    connection.send_result(msg["id"], _scene_result(hass, device, navigator.current()))


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/definitions"})
@websocket_api.async_response
@_require_server
async def _ws_definitions(hass, connection, msg) -> None:
    if not connection.user or not connection.user.is_admin:
        connection.send_error(msg["id"], "unauthorized", "Administrator access required")
        return
    connection.send_result(msg["id"], hass.data[DOMAIN].get("stored_definitions", {}))


@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/gallery", vol.Required("page"): dict,
     vol.Optional("entity"): str, vol.Optional("theme", default="ember"): str,
     vol.Optional("children", default=[]): [dict]}
)
@websocket_api.async_response
@_require_server
async def _ws_gallery(hass, connection, msg) -> None:
    if not connection.user or not connection.user.is_admin:
        connection.send_error(msg["id"], "unauthorized", "Administrator access required")
        return
    from .catalogue import NAV_STYLES, control_styles
    from .definition import build_definition
    from .scene import THEMES, compile_scene

    try:
        page = {**msg["page"], "id": "gallery", "parent": ""}
        page.pop("conditions", None)
        entity = msg.get("entity")
        if entity:
            entries = [*page.get("lights", []), *page.get("entities", [])]
            selected = next(item for item in entries if (item if isinstance(item, str) else item.get("entity_id")) == entity)
            if isinstance(selected, dict):
                selected = {key: value for key, value in selected.items() if key != "conditions"}
            page["entities"] = [selected]
            page.pop("lights", None)
        children = []
        if not entity:
            existing = len(page.get("entities", [])) + len(page.get("lights", []))
            children = msg.get("children", [])[:max(0, 8 - existing)]
            if not children and not existing:
                children = [{"title": name} for name in ("Rooms", "Lights", "Climate", "Media")]
            children = [{"id": f"gallery_{index}", "parent": "gallery", "title": item.get("title", "Page"), "icon": item.get("icon", "mdi:folder")} for index, item in enumerate(children)]
        nav = Navigator(definition=build_definition(hass, [page, *children], msg["theme"]))
        if entity:
            nav.input("press")
            _sync_control(hass, nav)
        view = nav.current()
        styles = sorted(control_styles(entity.split(".", 1)[0]) if entity else NAV_STYLES)
        connection.send_result(msg["id"], {
            "style": view.get("style"), "theme": view.get("theme"),
            "styles": {style: compile_scene({**view, "style": style}) for style in styles},
            "themes": {theme: compile_scene({**view, "theme": theme}) for theme in THEMES},
        })
    except (ValueError, TypeError, KeyError, StopIteration) as error:
        connection.send_error(msg["id"], "invalid_format", str(error))


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/subscribe",
        vol.Required("device"): DEVICE_SCHEMA,
        vol.Optional("definition"): dict,
    }
)
@websocket_api.async_response
@_require_server
async def _ws_subscribe(hass, connection, msg) -> None:
    device = msg["device"]
    state = hass.data[DOMAIN]
    if (
        _is_preview(device)
        and device not in state["definition_sources"]
        and "definition" in msg
    ):
        try:
            definition = _render_definition(hass, msg["definition"])
        except (TemplateError, TypeError, ValueError) as error:
            connection.send_error(msg["id"], "invalid_format", str(error))
            return
        await _install_definition(hass, device, msg["definition"], definition)

    @callback
    def changed(result):
        connection.send_event(msg["id"], result)

    unsubscribe = async_dispatcher_connect(hass, f"{DOMAIN}_scene_{device}", changed)

    @callback
    def remove():
        unsubscribe()
        if _is_preview(device):
            for cancel_time in state.get("condition_time_unsubs", {}).pop(device, []):
                cancel_time()
            if tracker := state.get("condition_trackers", {}).pop(device, None):
                tracker.async_remove()
            if tracker := state.get("template_trackers", {}).pop(device, None):
                tracker.async_remove()
            if watch := state.get("definition_unsubs", {}).pop(device, None):
                watch()
            for key in (
                "navigators",
                "definitions",
                "definition_sources",
                "revisions",
                "deployment_status",
            ):
                state.get(key, {}).pop(device, None)

    connection.subscriptions[msg["id"]] = remove
    connection.send_result(msg["id"])
    changed(_scene_result(hass, device, _navigator(hass, device).current()))
