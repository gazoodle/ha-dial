"""Commands a card or draft uses to show and operate a Dial, and those that change what it holds."""

from __future__ import annotations

import asyncio
import math

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError, TemplateError
from homeassistant.helpers.dispatcher import (
    async_dispatcher_connect,
    async_dispatcher_send,
)

from ..const import DOMAIN
from ..navigator import Navigator
from ..protocol import device_payload
from ..runtime import (
    _input,
    _install_definition,
    _is_preview,
    _navigator,
    _push,
    _render_definition,
    _scene_result,
    _sync_control,
)
from .common import DEVICE_SCHEMA, INPUTS, _require_server


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
        vol.Optional("live", default=False): bool,
    }
)
@websocket_api.async_response
@_require_server
async def _ws_input(hass, connection, msg) -> None:
    device = msg["device"]
    state = hass.data[DOMAIN]
    # A draft in the panel, operating real devices: for the same people who can edit it.
    if msg.get("live") and not (connection.user and connection.user.is_admin):
        connection.send_error(msg["id"], "unauthorized", "Administrator access required")
        return
    # A card browsing on its own holds the Dial's saved pages, so it acts as the Dial would.
    browsed = state.get("browsing", {}).get(device)
    if browsed is not None and state.get("stored_definitions", {}).get(browsed) is None:
        connection.send_error(msg["id"], "not_configured", "Dial has no active configuration")
        return
    if device in state.get("resetting", set()) or (device in state.get("stored_definitions", {}) and state["stored_definitions"][device] is None):
        connection.send_error(msg["id"], "not_configured", "Dial has no active configuration")
        return
    if msg.get("value") is not None and not math.isfinite(msg["value"]):
        connection.send_error(msg["id"], "invalid_format", "Value must be finite")
        return
    try:
        view = await _input(
            hass, msg["device"], msg["action"], msg.get("item"), msg.get("value"), live=msg.get("live", False) or browsed is not None
        )
    except HomeAssistantError as error:
        _sync_control(hass, _navigator(hass, msg["device"]))
        await _push(hass, msg["device"], _navigator(hass, msg["device"]).current())
        connection.send_error(msg["id"], "service_error", str(error))
        return
    connection.send_result(msg["id"], _scene_result(hass, msg["device"], view))


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
            if cancel_entities := state.get("condition_entity_unsubs", {}).pop(device, None):
                cancel_entities()
            for cancel_time in state.get("condition_time_unsubs", {}).pop(device, []):
                cancel_time()
            if tracker := state.get("condition_trackers", {}).pop(device, None):
                tracker.async_remove()
            if tracker := state.get("template_trackers", {}).pop(device, None):
                tracker.async_remove()
            if watch := state.get("definition_unsubs", {}).pop(device, None):
                watch()
            if watch := state.get("explorer_unsubs", {}).pop(device, None):
                watch()
            for key in (
                "navigators",
                "definitions",
                "definition_sources",
                "revisions",
                "deployment_status",
                "browsing",
            ):
                state.get(key, {}).pop(device, None)

    connection.subscriptions[msg["id"]] = remove
    connection.send_result(msg["id"])
    changed(_scene_result(hass, device, _navigator(hass, device).current()))


async def _refresh_browsing(hass, dial: str, source: dict) -> None:
    """Cards browsing a Dial on their own follow its saved pages, staying where they are if they can."""
    state = hass.data[DOMAIN]
    for session in [session for session, browsed in state.get("browsing", {}).items() if browsed == dial]:
        previous = state["navigators"].get(session)
        browsing = {**source, "preview_of": dial}
        navigator = await _install_definition(hass, session, browsing, _render_definition(hass, browsing))
        if previous:
            navigator.restore(previous)
        await _push(hass, session, navigator.current())


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/browse", vol.Required("device"): DEVICE_SCHEMA, vol.Required("dial"): DEVICE_SCHEMA})
@websocket_api.async_response
@_require_server
async def _ws_browse(hass, connection, msg) -> None:
    """Give a card its own screen on a Dial's saved pages. HA supplies the pages, so any card may ask."""
    state = hass.data[DOMAIN]
    session, dial = msg["device"], msg["dial"]
    browsing = state.setdefault("browsing", {})
    # Only a session of this kind, so this can't take over someone's draft in the panel.
    if not session.startswith("preview_") or _is_preview(dial) or (session in state["definition_sources"] and session not in browsing):
        connection.send_error(msg["id"], "invalid_format", "Not a card's own screen")
        return
    source = state.get("stored_definitions", {}).get(dial)
    if source is None:
        connection.send_error(msg["id"], "not_configured", "This Dial has no saved pages yet. Add them in the HA Dial panel.")
        return
    source = {**source, "preview_of": dial}
    try:
        definition = _render_definition(hass, source)
    except (TemplateError, TypeError, ValueError) as error:
        connection.send_error(msg["id"], "invalid_format", str(error))
        return
    browsing[session] = dial
    navigator = await _install_definition(hass, session, source, definition)
    connection.send_result(msg["id"], _scene_result(hass, session, navigator.current()))


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/configure",
        vol.Required("device"): DEVICE_SCHEMA,
        vol.Required("definition"): dict,
        vol.Optional("save", default=False): bool,
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
    # Only the panel may change a real Dial. A dashboard card once sent its own pages here whenever it
    # loaded, which replaced the Dial's saved tree (2026-11-01). Asking to save has to be deliberate, so
    # this also stops a browser still running an older card.
    if not _is_preview(device) and not msg.get("save"):
        connection.send_error(msg["id"], "not_allowed", "Pages for a real Dial are saved from the HA Dial panel")
        return
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
    if device in state.get("resetting", set()):
        connection.send_error(msg["id"], "busy", "Dial is being reset")
        return
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
            await _refresh_browsing(hass, device, source)
    else:
        navigator = await _install_definition(
            hass, device, source, definition, push=True
        )
    connection.send_result(msg["id"], _scene_result(hass, device, navigator.current()))


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/reset", vol.Required("device"): DEVICE_SCHEMA})
@websocket_api.async_response
@_require_server
async def _ws_reset(hass, connection, msg) -> None:
    if not connection.user or not connection.user.is_admin:
        connection.send_error(msg["id"], "unauthorized", "Administrator access required")
        return
    device = msg["device"]
    if _is_preview(device):
        connection.send_error(msg["id"], "invalid_format", "Choose a physical Dial")
        return
    state = hass.data[DOMAIN]
    from ..transport import async_clear_view

    async with state.setdefault("definition_lock", asyncio.Lock()):
        if not state["active"]:
            connection.send_error(msg["id"], "not_loaded", "HA Dial Server was unloaded")
            return
        resetting = state.setdefault("resetting", set())
        resetting.add(device)
        try:
            stored = {**state.get("stored_definitions", {}), device: None}
            await state["definition_store"].async_save(stored)
            state["stored_definitions"] = stored
            state.get("pending_scenes", {}).pop(device, None)
            if worker := state.get("scene_workers", {}).get(device):
                await asyncio.shield(worker)
            for key in ("template_trackers", "condition_trackers"):
                if tracker := state.get(key, {}).pop(device, None):
                    tracker.async_remove()
            for key in ("condition_entity_unsubs", "definition_unsubs", "explorer_unsubs"):
                if unsubscribe := state.get(key, {}).pop(device, None):
                    unsubscribe()
            for unsubscribe in state.get("condition_time_unsubs", {}).pop(device, []):
                unsubscribe()
            for key in ("definitions", "definition_sources", "navigators", "deployment_status", "input_sequences"):
                state.get(key, {}).pop(device, None)
            cleared = await async_clear_view(hass, device)
            for session, browsed in state.get("browsing", {}).items():
                if browsed == device:
                    async_dispatcher_send(hass, f"{DOMAIN}_scene_{session}", {"error": "This Dial has no saved pages yet. Add them in the HA Dial panel."})
        finally:
            resetting.discard(device)
    connection.send_result(msg["id"], {"cleared": cleared})
