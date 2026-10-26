"""HA Dial integration: HA owns navigation and sends only the current view."""

from __future__ import annotations

import json
import math
import re
from datetime import timedelta
from pathlib import Path

import voluptuous as vol
from homeassistant.components import frontend, websocket_api
from homeassistant.components.light import ATTR_BRIGHTNESS
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_FRIENDLY_NAME, CONF_ENTITY_ID, STATE_ON
from homeassistant.core import Event, HomeAssistant, State, callback
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval

from .const import CARD_URL, DEVICE_EVENT, DOMAIN, VERSION
from .deployment import manifest_version, revision
from .navigator import Navigator
from .restart_notice import async_check_restart

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
}
DEVICE_RE = re.compile(r"^[a-z0-9_]{1,64}$")
DEVICE_SCHEMA = vol.All(str, vol.Match(DEVICE_RE))


def _navigator(hass: HomeAssistant, device: str) -> Navigator:
    state = hass.data[DOMAIN]
    return state["navigators"].setdefault(
        device, Navigator(state.get("light_entity"), state.get("light_name", "Light"))
    )


def _light_values(state: State | None) -> tuple[int, bool, bool]:
    if state is None or state.state in {"unknown", "unavailable"}:
        return 0, False, False
    active = state.state == STATE_ON
    brightness = state.attributes.get(ATTR_BRIGHTNESS)
    value = (
        round(brightness * 100 / 255)
        if isinstance(brightness, (int, float))
        else 100 if active else 0
    )
    return value, active, True


def _sync_light(hass: HomeAssistant, navigator: Navigator) -> None:
    view = navigator.current()
    if view.get("kind") == "control":
        navigator.sync(*_light_values(hass.states.get(view["entity_id"])))


async def _input(
    hass: HomeAssistant,
    device: str,
    action: str,
    item: str | None = None,
    value: float | None = None,
    push: bool = True,
) -> dict:
    navigator = _navigator(hass, device)
    was_control = navigator.current().get("kind") == "control"
    if action == "ready":
        _sync_light(hass, navigator)
    view = navigator.input(action, item, value)
    if was_control and view.get("available"):
        if action in {"rotate_left", "rotate_right", "set_value"}:
            await hass.services.async_call(
                "light",
                "turn_on",
                {"entity_id": view["entity_id"], "brightness_pct": view["value"]},
            )
        elif action == "press":
            await hass.services.async_call(
                "light",
                "turn_on" if view["active"] else "turn_off",
                {"entity_id": view["entity_id"]},
            )
    if not was_control:
        _sync_light(hass, navigator)
        view = navigator.current()
    if push:
        await _push(hass, device, view)
    return view


async def _push(hass: HomeAssistant, device: str, view: dict) -> None:
    service = f"{device}_ha_dial_show_view"
    if DEVICE_RE.fullmatch(device) and hass.services.has_service("esphome", service):
        await hass.services.async_call(
            "esphome", service, {"view": json.dumps(view, separators=(",", ":"))}
        )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    state = hass.data.setdefault(DOMAIN, {"navigators": {}, "registered": False})
    light_entity = entry.options.get(CONF_ENTITY_ID, entry.data.get(CONF_ENTITY_ID))
    light_state = hass.states.get(light_entity) if light_entity else None
    state.update(
        light_entity=light_entity,
        light_name=(light_state.attributes.get(ATTR_FRIENDLY_NAME) if light_state else None)
        or (light_entity.split(".", 1)[-1].replace("_", " ").title() if light_entity else "Light"),
    )
    state["navigators"].clear()
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
        value = event.data.get("value")
        if action == "set_value":
            try:
                value = float(value)
            except (TypeError, ValueError):
                return
            if not math.isfinite(value):
                return
        else:
            value = None
        hass.async_create_task(
            _input(
                hass,
                device,
                action,
                item if isinstance(item, str) else None,
                value,
                push=action != "set_value",
            )
        )

    entry.async_on_unload(hass.bus.async_listen(DEVICE_EVENT, device_input))

    if light_entity:

        async def light_changed(_event: Event) -> None:
            for device, navigator in state["navigators"].items():
                _sync_light(hass, navigator)
                await _push(hass, device, navigator.current())

        entry.async_on_unload(
            async_track_state_change_event(hass, [light_entity], light_changed)
        )

    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))

    async def check_restart(_now=None) -> None:
        await async_check_restart(hass, LOADED_VERSION, LOADED_REVISION)

    await check_restart()
    entry.async_on_unload(async_track_time_interval(hass, check_restart, timedelta(seconds=30)))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return True


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


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
        vol.Optional("value"): vol.Coerce(float),
    }
)
@websocket_api.async_response
async def _ws_input(hass, connection, msg) -> None:
    view = await _input(
        hass, msg["device"], msg["action"], msg.get("item"), msg.get("value")
    )
    connection.send_result(msg["id"], view)
