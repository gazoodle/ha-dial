"""HA-owned navigation, scene publishing and live definition tracking."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from time import time_ns

from homeassistant.const import ATTR_FRIENDLY_NAME
from homeassistant.core import (
    Event,
    EventStateChangedData,
    HomeAssistant,
    callback,
)
from homeassistant.exceptions import HomeAssistantError, TemplateError
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import (
    TrackTemplate,
    async_track_state_change_event,
    async_track_template_result,
    async_track_time_change,
)

from .catalogue import CHRONOGRAPH_STYLES, FACE_STYLES
from .chronograph import resolve_clock, source_entities
from .const import DOMAIN
from .controls import control_command, control_state, preview_feedback
from .definition import THEMES, build_definition, leaf_items, validate_definition
from .frames import cancel_capture, mark_stale, request_frame, scene_frames
from .history import ensure_history, forget_history, record_change
from .navigator import Navigator
from .protocol import device_payload
from .scene import compile_scene
from .visibility import filter_definition

_LOGGER = logging.getLogger(__name__)
REGISTRY_SETTLE_SECONDS = 1


def _navigator(hass: HomeAssistant, device: str) -> Navigator:
    state = hass.data[DOMAIN]
    light_entity = state.get("light_entity")
    light_state = hass.states.get(light_entity) if light_entity else None
    light_name = (
        light_state.attributes.get(ATTR_FRIENDLY_NAME) if light_state else None
    ) or state.get("light_name", "Light")
    if device not in state["navigators"]:
        state["navigators"][device] = Navigator(
            light_entity, light_name, state.get("definitions", {}).get(device)
        )
    navigator = state["navigators"][device]
    navigator.settings_enabled = state.get("settings_enabled", {}).get(
        state.get("definition_sources", {}).get(device, {}).get("preview_of", device)
        if _is_preview(device)
        else device,
        False,
    )
    return navigator


def _is_preview(device: str) -> bool:
    return device == "preview" or device.startswith("preview_")


def _sync_control(hass: HomeAssistant, navigator: Navigator) -> None:
    view = navigator.current()
    if view.get("kind") == "control":
        properties = control_state(
            view["entity_id"], hass.states.get(view["entity_id"])
        )
        properties["confirm"] = view.get("domain") in {
            "lock",
            "alarm_control_panel",
        } or view.get("confirm", False)
        navigator.sync(**properties)


async def _input(
    hass: HomeAssistant,
    device: str,
    action: str,
    item: str | None = None,
    value: float | None = None,
    push: bool = True,
    input_sequence: int | None = None,
) -> dict:
    if hass.data[DOMAIN].get("unloading"):
        return _navigator(hass, device).current()
    state = hass.data[DOMAIN]
    if device in state.get("resetting", set()) or (device in state.get("stored_definitions", {}) and state["stored_definitions"][device] is None):
        return {}
    sequences = hass.data[DOMAIN].setdefault("input_sequences", {})
    if input_sequence is not None:
        if action != "ready" and input_sequence <= sequences.get(device, -1):
            return _navigator(hass, device).current()
        sequences[device] = input_sequence
    navigator = _navigator(hass, device)
    before = navigator.current()
    was_control = before.get("kind") == "control"
    if action == "ready":
        _sync_control(hass, navigator)
    view = navigator.input(action, item, value)
    # A camera's button opens another control with this same press. That press chose the control and
    # must not also operate it: without this, opening a light from a camera would toggle the light.
    if was_control and view.get("id") != before.get("id"):
        was_control = False
    if _is_preview(device) and navigator.control is not None:
        if was_control:
            preview_feedback(navigator.control, action, item)
        navigator.control["pending"] = False
        navigator.control.pop("target_value", None)
        view = navigator.current()
    if not was_control:
        _sync_control(hass, navigator)
        view = navigator.current()
    if (
        was_control
        and view.get("kind") == "control"
        and not _is_preview(device)
        and (command := control_command(view, action, item))
    ):
        domain, service, data = command
        try:
            await hass.services.async_call(domain, service, data)
        except HomeAssistantError:
            if navigator.control is not None and navigator.control.get(
                "target_value"
            ) == view.get("target_value"):
                navigator.control.pop("target_value", None)
                _sync_control(hass, navigator)
                await _push(hass, device, navigator.current())
            raise
    if push:
        await _push(hass, device, view)
    return navigator.current()


def _next_revision(hass: HomeAssistant, device: str) -> int:
    revisions = hass.data[DOMAIN].setdefault("revisions", {})
    revisions[device] = max(time_ns() // 1_000_000, revisions.get(device, 0) + 1)
    return revisions[device]


async def _push(hass: HomeAssistant, device: str, view: dict) -> None:
    state = hass.data[DOMAIN]
    if state.get("unloading") or device in state.get("resetting", set()) or (device in state.get("stored_definitions", {}) and state["stored_definitions"][device] is None):
        return
    await ensure_history(hass, view)

    async def republish():
        await _push(hass, device, _navigator(hass, device).current())

    request_frame(hass, device, view, republish)
    view = resolve_clock(hass, view)
    _navigator(hass, device).clock_snapshot = view if view.get("style") in FACE_STYLES else None
    revision = _next_revision(hass, device)
    service = f"{device}_ha_dial_show_view"
    connected = (
        not _is_preview(device)
        and hass.services.has_service("esphome", service)
        and state.get("transport_available", {}).get(device, True)
    )
    state.setdefault("deployment_status", {})[device] = (
        "sent" if connected else "preview" if _is_preview(device) else "waiting"
    )
    async_dispatcher_send(
        hass, f"{DOMAIN}_scene_{device}", _scene_result(hass, device, view)
    )
    if connected:
        state.setdefault("pending_scenes", {})[device] = (
            view,
            resolve_clock(hass, previous) if (previous := _navigator(hass, device).previous()) else None,
            revision,
            state.get("input_sequences", {}).get(device, 0),
        )
        workers = state.setdefault("scene_workers", {})
        if device not in workers:
            # Store ownership before the worker can finish and remove itself.
            workers[device] = hass.async_create_task(
                _send_scenes(hass, device), eager_start=False
            )
        await asyncio.shield(workers[device])


async def _send_scenes(hass: HomeAssistant, device: str) -> None:
    """One in-flight scene and one replaceable latest scene; never replay a backlog."""
    state = hass.data[DOMAIN]
    pending = state["pending_scenes"]
    try:
        while device in pending:
            view, previous, revision, sequence = pending.pop(device)
            try:
                payload = device_payload(resolve_clock(hass, view), resolve_clock(hass, previous) if previous else None, revision, sequence)
                async with asyncio.timeout(10):
                    await hass.services.async_call(
                        "esphome",
                        f"{device}_ha_dial_show_view",
                        {"view": payload},
                        blocking=True,
                    )
            except (HomeAssistantError, TimeoutError, ValueError) as error:
                _LOGGER.warning(
                    "Could not send HA Dial scene for %s: %s", device, error
                )
                if state["revisions"].get(device) == revision:
                    state["deployment_status"][device] = "failed"
                    async_dispatcher_send(
                        hass,
                        f"{DOMAIN}_scene_{device}",
                        _scene_result(hass, device, _navigator(hass, device).current()),
                    )
    finally:
        state["scene_workers"].pop(device, None)
        pending.pop(device, None)


def _scene_result(hass: HomeAssistant, device: str, view: dict) -> dict:
    state = hass.data[DOMAIN]
    snapshot = _navigator(hass, device).clock_snapshot
    if snapshot and (snapshot.get("id"), snapshot.get("style")) == (view.get("id"), view.get("style")):
        view = {**view, "_clock": snapshot["_clock"]}
    scene = compile_scene(resolve_clock(hass, view))
    return {
        "scene": scene,
        "frames": scene_frames(hass, scene),
        "frame_error": state.get("frame_status", {}).get(device, ""),
        "revision": state.get("revisions", {}).get(device, 0),
        "deployment": state.get("deployment_status", {}).get(
            device, "preview" if _is_preview(device) else "waiting"
        ),
    }


def _render_definition(hass: HomeAssistant, source: dict) -> dict:
    preview_of = source.get("preview_of")
    if preview_of is not None and (
        not isinstance(preview_of, str)
        or re.fullmatch(r"[a-z0-9_]{1,64}", preview_of) is None
    ):
        raise ValueError("Preview source must identify a valid Dial device")
    if not isinstance(source.get("template", ""), str):
        raise TypeError("Template must be text")
    if source.get("theme", "ember") not in THEMES:
        raise ValueError("Unknown default theme")
    if not source.get("template"):
        return filter_definition(
            hass,
            build_definition(
                hass, source.get("pages", []), source.get("theme", "ember")
            ),
        )
    from homeassistant.helpers.template import Template

    return filter_definition(
        hass,
        _template_definition(
            Template(source["template"], hass).async_render(
                variables={
                    "theme": source.get("theme", "ember"),
                    "pages": source.get("pages", []),
                },
                parse_result=True,
            )
        ),
    )


def _template_definition(result) -> dict:
    definition = json.loads(result) if isinstance(result, str) else result
    validate_definition(definition)
    return definition


def _watch_home(hass: HomeAssistant, device: str, rebuild) -> None:
    """Rebuild an Explorer when the home's structure changes. A bulk change arrives as many events."""
    from homeassistant.helpers import area_registry as ar
    from homeassistant.helpers import device_registry as dr
    from homeassistant.helpers import entity_registry as er
    from homeassistant.helpers import floor_registry as fr
    from homeassistant.helpers.event import async_call_later
    from homeassistant.helpers.start import async_at_started

    pending = None

    @callback
    def fire(_now) -> None:
        nonlocal pending
        pending = None
        rebuild(None)

    @callback
    def changed(_event=None) -> None:
        nonlocal pending
        if pending:
            pending()
        pending = async_call_later(hass, REGISTRY_SETTLE_SECONDS, fire)

    cancels = [
        hass.bus.async_listen(event, changed)
        for event in (ar.EVENT_AREA_REGISTRY_UPDATED, dr.EVENT_DEVICE_REGISTRY_UPDATED, er.EVENT_ENTITY_REGISTRY_UPDATED, fr.EVENT_FLOOR_REGISTRY_UPDATED)
    ]
    # YAML and helper entities only appear as states, and most have appeared by the time HA has started.
    if not hass.is_running:
        cancels.append(async_at_started(hass, changed))

    def unsubscribe() -> None:
        if pending:
            pending()
        for cancel in cancels:
            cancel()

    hass.data[DOMAIN].setdefault("explorer_unsubs", {})[device] = unsubscribe


def _watch_definition_entities(
    hass: HomeAssistant, device: str, definition: dict
) -> None:
    state = hass.data[DOMAIN]
    unsubs = state.setdefault("definition_unsubs", {})
    if unsubscribe := unsubs.pop(device, None):
        unsubscribe()
    forget_history(hass)
    entities = {item["entity_id"] for item in leaf_items(definition["tree"])}
    faces = [view for view in state["navigators"][device].views.values() if view.get("style") in FACE_STYLES]
    # A camera in the tree is a face too: its sources and age need the same events and minute tick.
    leaves = list(leaf_items(definition["tree"]))
    faces += [item for item in leaves if item.get("style") in FACE_STYLES]
    for view in faces:
        entities |= source_entities(view)
    entities |= {action["entity_id"] for item in leaves for action in item.get("action_items", [])}
    # Seconds are only pushed for faces that show them; every other face redraws on the minute.
    seconds = any(view["style"] in CHRONOGRAPH_STYLES for view in faces)

    async def entity_changed(_event: Event[EventStateChangedData]) -> None:
        navigator = state["navigators"].get(device)
        if navigator is None:
            return
        current = navigator.current()
        entity = _event.data.get("entity_id")
        record_change(hass, entity, _event.data.get("new_state"), current.get("clock", {}).get("history_hours", 24))
        if entity is not None:
            mark_stale(hass, entity)
        if entity != current.get("entity_id") and entity not in source_entities(current):
            return
        _sync_control(hass, navigator)
        await _push(hass, device, navigator.current())

    async def clock_changed(now):
        navigator = state["navigators"].get(device)
        if navigator is None or state.get("unloading"):
            return
        style = navigator.current().get("style")
        if style in CHRONOGRAPH_STYLES or (style in FACE_STYLES and now.second == 0):
            await _push(hass, device, navigator.current())

    cleanup = []
    try:
        if entities:
            cleanup.append(async_track_state_change_event(hass, entities, entity_changed))
        if faces:
            cleanup.append(async_track_time_change(hass, clock_changed, second="*" if seconds else 0))
    except Exception:
        for cancel in cleanup:
            cancel()
        raise

    def unsubscribe():
        cancel_capture(hass, device)
        for cancel in cleanup:
            cancel()

    unsubs[device] = unsubscribe


async def _install_definition(
    hass: HomeAssistant,
    device: str,
    source: dict,
    definition: dict,
    *,
    push: bool = False,
) -> Navigator:
    state = hass.data[DOMAIN]
    navigator = Navigator(
        state.get("light_entity"), state.get("light_name", "Light"), definition
    )
    navigator.settings_enabled = state.get("settings_enabled", {}).get(
        source.get("preview_of", device) if _is_preview(device) else device, False
    )
    state["definitions"][device] = definition
    state["definition_sources"][device] = source
    state["navigators"][device] = navigator
    if push:
        await _push(hass, device, navigator.current())
    _watch_definition_entities(hass, device, definition)

    trackers = state.setdefault("template_trackers", {})
    if tracker := trackers.pop(device, None):
        tracker.async_remove()

    from homeassistant.helpers.template import Template

    variables = {
        "theme": source.get("theme", "ember"),
        "pages": source.get("pages", []),
    }

    @callback
    def template_changed(_event, updates) -> None:
        if (
            state.get("unloading")
            or state["definition_sources"].get(device) is not source
        ):
            return
        result = updates[-1].result
        if isinstance(result, TemplateError):
            _LOGGER.error("HA Dial template failed for device %s: %s", device, result)
            async_dispatcher_send(
                hass, f"{DOMAIN}_scene_{device}", {"error": str(result)}
            )
            return
        try:
            updated = filter_definition(hass, _template_definition(result))
        except (TypeError, ValueError, json.JSONDecodeError) as error:
            _LOGGER.warning(
                "Ignoring invalid HA Dial template update for %s: %s", device, error
            )
            async_dispatcher_send(
                hass, f"{DOMAIN}_scene_{device}", {"error": str(error)}
            )
            return
        if updated == state["definitions"].get(device):
            return
        current = state["navigators"].get(device)
        updated_navigator = Navigator(
            state.get("light_entity"), state.get("light_name", "Light"), updated
        )
        updated_navigator.settings_enabled = state.get("settings_enabled", {}).get(
            device, False
        )
        if current:
            updated_navigator.restore(current)
        if updated_navigator.control is not None:
            _sync_control(hass, updated_navigator)
        state["definitions"][device] = updated
        state["navigators"][device] = updated_navigator
        watch_condition_times(updated)
        watch_condition_entities(updated)
        _watch_definition_entities(hass, device, updated)
        hass.async_create_task(_push(hass, device, updated_navigator.current()))

    condition_trackers = state.setdefault("condition_trackers", {})
    if old_tracker := condition_trackers.pop(device, None):
        old_tracker.async_remove()
    condition_sources = definition.get("_condition_templates", [])

    @callback
    def conditions_changed(_event, _updates=None):
        if (
            state.get("unloading")
            or state["definition_sources"].get(device) is not source
        ):
            return
        try:
            updated = _render_definition(hass, source)
            # A registry event is often about something the Dial doesn't show, such as a firmware version.
            if updated == state["definitions"].get(device):
                return
            current = state["navigators"].get(device)
            replacement = Navigator(definition=updated)
            replacement.settings_enabled = state.get("settings_enabled", {}).get(
                device, False
            )
            if current:
                replacement.restore(current)
            _sync_control(hass, replacement)
            state["navigators"][device] = replacement
            state["definitions"][device] = updated
            _watch_definition_entities(hass, device, updated)
            hass.async_create_task(_push(hass, device, replacement.current()))
        except (TemplateError, ValueError, TypeError) as error:
            _LOGGER.error("HA Dial visibility failed: %s", error)
            async_dispatcher_send(
                hass, f"{DOMAIN}_scene_{device}", {"error": str(error)}
            )

    def watch_condition_times(current_definition):
        time_unsubs = state.setdefault("condition_time_unsubs", {})
        for unsubscribe in time_unsubs.pop(device, []):
            unsubscribe()
        time_unsubs[device] = [
            async_track_time_change(hass, conditions_changed, hour=int(hour), minute=int(minute), second=int(second))
            for hour, minute, second in (value.split(":") for value in current_definition.get("_condition_times", []))
        ]

    def watch_condition_entities(current_definition):
        unsubs = state.setdefault("condition_entity_unsubs", {})
        if unsubscribe := unsubs.pop(device, None):
            unsubscribe()
        entities = current_definition.get("_condition_entities", [])
        if entities:
            unsubs[device] = async_track_state_change_event(hass, entities, conditions_changed)

    watch_condition_times(definition)
    watch_condition_entities(definition)
    if unsubscribe_home := state.setdefault("explorer_unsubs", {}).pop(device, None):
        unsubscribe_home()
    if any("explorer" in page for page in source.get("pages", [])) and not source.get("template"):
        _watch_home(hass, device, conditions_changed)
    if condition_sources:
        condition_trackers[device] = async_track_template_result(
            hass,
            [TrackTemplate(Template(text, hass), {}) for text in condition_sources],
            conditions_changed,
        )
        condition_trackers[device].async_refresh()

    if source.get("template"):
        tracker = async_track_template_result(
            hass,
            [TrackTemplate(Template(source["template"], hass), variables)],
            template_changed,
        )
        trackers[device] = tracker
        tracker.async_refresh()
    return navigator
