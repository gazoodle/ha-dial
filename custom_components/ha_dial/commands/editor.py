"""Commands only the panel uses, to read a Dial's saved pages and to preview choices."""

from __future__ import annotations

import voluptuous as vol
from homeassistant.components import websocket_api

from ..const import DOMAIN
from ..navigator import Navigator
from ..runtime import _sync_control
from .common import _require_server


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/definitions"})
@websocket_api.async_response
@_require_server
async def _ws_definitions(hass, connection, msg) -> None:
    if not connection.user or not connection.user.is_admin:
        connection.send_error(msg["id"], "unauthorized", "Administrator access required")
        return
    connection.send_result(msg["id"], {device: source for device, source in hass.data[DOMAIN].get("stored_definitions", {}).items() if source is not None})


@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/gallery", vol.Required("page"): dict,
     vol.Optional("entity"): str, vol.Optional("theme", default="ember"): str,
     vol.Optional("children", default=[]): [dict], vol.Optional("preview_only", default=False): bool,
     vol.Optional("nav_only", default=False): bool, vol.Optional("long", default=False): bool}
)
@websocket_api.async_response
@_require_server
async def _ws_gallery(hass, connection, msg) -> None:
    if not connection.user or not connection.user.is_admin:
        connection.send_error(msg["id"], "unauthorized", "Administrator access required")
        return
    from ..catalogue import (
        IMAGE_STYLES,
        NAV_STYLES,
        PAGE_STYLES,
        PAGED_STYLES,
        control_styles,
    )
    from ..chronograph import resolve_clock
    from ..definition import build_definition
    from ..frames import capture, frame_key, scene_frames
    from ..history import ensure_history
    from ..scene import THEMES, compile_scene

    try:
        page = {**msg["page"], "id": "gallery", "parent": ""}
        page.pop("conditions", None)
        # Thumbnails of an Explorer's pages use stand-in children; they needn't rebuild the home.
        page.pop("explorer", None)
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
            if not children and not existing and not msg.get("preview_only"):
                children = [{"title": name} for name in ("Rooms", "Lights", "Climate", "Media")]
            children = [{"id": f"gallery_{index}", "parent": "gallery", "title": item.get("title", "Page"), "icon": item.get("icon", "mdi:folder")} for index, item in enumerate(children)]
        nav = Navigator(definition=build_definition(hass, [page, *children], msg["theme"]))
        if entity:
            nav.input("press")
            _sync_control(hass, nav)
        await ensure_history(hass, nav.current())
        # A live preview only needs the style on show; the gallery needs them all.
        for style in {nav.current().get("style")} if msg.get("preview_only") else IMAGE_STYLES:
            candidate = {**nav.current(), "style": style}
            if (key := frame_key(candidate)) and key not in hass.data[DOMAIN].get("frames", {}):
                await capture(hass, candidate, key)
        view = resolve_clock(hass, nav.current())
        if msg.get("preview_only"):
            scene = compile_scene(view)
            connection.send_result(msg["id"], {"scene": scene, "frames": scene_frames(hass, scene)})
            return
        styles = sorted(control_styles(entity.split(".", 1)[0]) if entity else PAGED_STYLES if msg.get("long") else NAV_STYLES if msg.get("nav_only") else PAGE_STYLES)
        # From the unresolved view: a resolved one carries the selected style's picture, and every
        # thumbnail would then show that one treatment.
        unresolved = nav.current()
        style_scenes = {style: compile_scene(resolve_clock(hass, {**unresolved, "style": style})) for style in styles}
        connection.send_result(msg["id"], {
            "style": view.get("style"), "theme": view.get("theme"),
            "frames": {key: value for scene in style_scenes.values() for key, value in scene_frames(hass, scene).items()},
            "styles": style_scenes,
            "themes": {theme: compile_scene({**view, "theme": theme}) for theme in THEMES},
        })
    except (ValueError, TypeError, KeyError, StopIteration) as error:
        connection.send_error(msg["id"], "invalid_format", str(error))


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/explorer", vol.Required("options"): dict, vol.Optional("style", default="NAV-LIST"): str})
@websocket_api.async_response
@_require_server
async def _ws_explorer(hass, connection, msg) -> None:
    """What an Explorer would show right now, and what it leaves out and why."""
    if not connection.user or not connection.user.is_admin:
        connection.send_error(msg["id"], "unauthorized", "Administrator access required")
        return
    from ..explorer import explore, outline, page_style, read_home, validate_explorer

    try:
        validate_explorer(msg["options"])
        items, counts = explore(read_home(hass), msg["options"], {"style": msg["style"], "theme": "ember"})
    except (TypeError, ValueError) as error:
        connection.send_error(msg["id"], "invalid_format", str(error))
        return
    connection.send_result(msg["id"], {"items": outline(items), "style": page_style("", len(items), msg["style"], msg["options"]), **counts})


@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/condition_template", vol.Required("condition"): dict}
)
@websocket_api.async_response
@_require_server
async def _ws_condition_template(hass, connection, msg) -> None:
    if not connection.user or not connection.user.is_admin:
        connection.send_error(msg["id"], "unauthorized", "Administrator access required")
        return
    from ..visibility import condition_template

    try:
        source = condition_template(msg["condition"])
    except (ValueError, TypeError, KeyError) as error:
        connection.send_error(msg["id"], "invalid_condition", str(error))
        return
    connection.send_result(msg["id"], source)
