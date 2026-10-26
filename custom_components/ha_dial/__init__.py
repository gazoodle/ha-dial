"""HA Dial integration: HA owns navigation and sends only the current view."""

from __future__ import annotations

import json
import re
from datetime import timedelta
from pathlib import Path

import voluptuous as vol
from homeassistant.components import frontend, websocket_api
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_interval

from .const import CARD_URL, DEVICE_EVENT, DOMAIN, VERSION
from .deployment import manifest_version, revision
from .navigator import Navigator
from .restart_notice import async_check_restart

LOADED_VERSION = manifest_version(Path(__file__).parent)
LOADED_REVISION = revision(Path(__file__).parent)
INPUTS = {"ready", "rotate_left", "rotate_right", "press", "touch", "back"}
DEVICE_RE = re.compile(r"^[a-z0-9_]{1,64}$")
DEVICE_SCHEMA = vol.All(str, vol.Match(DEVICE_RE))


def _navigator(hass: HomeAssistant, device: str) -> Navigator:
    return hass.data[DOMAIN]["navigators"].setdefault(device, Navigator())


async def _push(hass: HomeAssistant, device: str, view: dict) -> None:
    service = f"{device}_ha_dial_show_view"
    if DEVICE_RE.fullmatch(device) and hass.services.has_service("esphome", service):
        await hass.services.async_call(
            "esphome", service, {"view": json.dumps(view, separators=(",", ":"))}
        )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    state = hass.data.setdefault(DOMAIN, {"navigators": {}, "registered": False})
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
        state["registered"] = True

    url = f"{CARD_URL}?v={VERSION}"
    frontend.add_extra_js_url(hass, url)
    entry.async_on_unload(lambda: frontend.remove_extra_js_url(hass, url))

    @callback
    def device_input(event: Event) -> None:
        device = event.data.get("device")
        action = event.data.get("action")
        if not isinstance(device, str) or DEVICE_RE.fullmatch(device) is None:
            return
        if not isinstance(action, str) or action not in INPUTS:
            return
        item = event.data.get("item")
        view = _navigator(hass, device).input(action, item if isinstance(item, str) else None)
        hass.async_create_task(_push(hass, device, view))

    entry.async_on_unload(hass.bus.async_listen(DEVICE_EVENT, device_input))

    async def check_restart(_now=None) -> None:
        await async_check_restart(hass, LOADED_VERSION, LOADED_REVISION)

    await check_restart()
    entry.async_on_unload(async_track_time_interval(hass, check_restart, timedelta(seconds=30)))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return True


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/view",
        vol.Optional("device", default="preview"): DEVICE_SCHEMA,
    }
)
@websocket_api.async_response
async def _ws_view(hass, connection, msg) -> None:
    connection.send_result(msg["id"], _navigator(hass, msg["device"]).current())


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/input",
        vol.Optional("device", default="preview"): DEVICE_SCHEMA,
        vol.Required("action"): vol.In(INPUTS),
        vol.Optional("item"): str,
    }
)
@websocket_api.async_response
async def _ws_input(hass, connection, msg) -> None:
    view = _navigator(hass, msg["device"]).input(msg["action"], msg.get("item"))
    await _push(hass, msg["device"], view)
    connection.send_result(msg["id"], view)
