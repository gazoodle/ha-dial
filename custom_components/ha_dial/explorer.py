"""Explorer: a page whose items HA builds from the home's floors, areas and entities.

An Explorer takes one slot on a page, beside the owner's own items and pages. `read_home` is the only
part that touches HA; everything after it is plain data, so the rules can be tested on any home.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from hashlib import sha256

from .appearance import CHOICES, validate_options
from .assets import usable_icon
from .catalogue import CAMERA_STYLES, CONTROL_TYPES, NAV_STYLES, PAGED_STYLES

MAX_SHOWN = 8  # A page over this needs a style that scrolls or pages, and an area splits by function.
ASSISTANT = "conversation"
HIDDEN_CATEGORIES = {"config", "diagnostic"}
CONFIRMED_COVERS = {"garage", "gate", "door"}
SECURITY_DOMAINS = {"lock", "alarm_control_panel"}
PICTURE_DOMAINS = {"camera", "image"}
FIELDS = {"floor_id", "area_id", "assist_only", "include_security", "exclude", "random", "shuffle", "long_style", "camera_style", "picture_mode", "pages"}
OVERRIDE_FIELDS = {"style", "theme", "icon", "appearance", "css"}
DEFAULT_LONG_STYLE = "NAV-LIST"
# Order on a page; anything else goes in Other.
FUNCTIONS = (
    ("Lights", "mdi:lightbulb", {"light"}),
    ("Climate", "mdi:thermometer", {"climate", "fan"}),
    ("Media", "mdi:play-circle", {"media_player"}),
    ("Covers", "mdi:blinds", {"cover"}),
    ("Security", "mdi:shield-home", {"lock", "alarm_control_panel", "camera", "image"}),
    ("Switches", "mdi:toggle-switch", {"switch"}),
    ("Scenes", "mdi:palette", {"scene", "button", "input_button"}),
    ("Sensors", "mdi:chart-line", {"sensor", "binary_sensor", "weather"}),
)
OTHER = ("Other", "mdi:dots-horizontal", set())
FLOOR_ICONS = {-1: "mdi:home-floor-negative-1", 0: "mdi:home-floor-g", 1: "mdi:home-floor-1", 2: "mdi:home-floor-2", 3: "mdi:home-floor-3"}


@dataclass(frozen=True)
class Floor:
    id: str
    name: str
    level: int | None = None
    icon: str | None = None


@dataclass(frozen=True)
class Area:
    id: str
    name: str
    floor_id: str | None = None
    icon: str | None = None


@dataclass(frozen=True)
class Entity:
    entity_id: str
    name: str
    area_id: str | None = None
    icon: str | None = None
    device_class: str | None = None
    category: str | None = None
    hidden: bool = False
    disabled: bool = False
    # What Assist's settings say, or None where nothing has been saved. HA's own lookup would save a
    # default, and Explorer must never change exposure settings.
    exposed: bool | None = None


@dataclass
class Home:
    floors: list[Floor] = field(default_factory=list)
    areas: list[Area] = field(default_factory=list)
    entities: list[Entity] = field(default_factory=list)


def validate_explorer(options) -> None:
    if not isinstance(options, dict) or set(options) - FIELDS:
        raise ValueError("Unknown Explorer setting")
    for name in ("floor_id", "area_id"):
        if not isinstance(options.get(name, ""), str):
            raise TypeError(f"{name} must be text")
    if options.get("floor_id") and options.get("area_id"):
        raise ValueError("An Explorer covers one floor or one area, not both")
    for name in ("assist_only", "include_security", "random"):
        if not isinstance(options.get(name, False), bool):
            raise TypeError(f"{name} must be on or off")
    if isinstance(options.get("shuffle", 0), bool) or not isinstance(options.get("shuffle", 0), int):
        raise TypeError("shuffle must be a whole number")
    if options.get("long_style", DEFAULT_LONG_STYLE) not in PAGED_STYLES:
        raise ValueError("Pages over 8 items need a style that scrolls or pages")
    if options.get("camera_style", "CAM-PORTAL") not in CAMERA_STYLES:
        raise ValueError("Unknown camera style")
    if "picture_mode" in options and options["picture_mode"] not in CHOICES["picture-mode"][2]:
        raise ValueError("Unknown picture treatment")
    exclude = options.get("exclude", [])
    if not isinstance(exclude, list) or not all(isinstance(entity, str) and re.fullmatch(r"[a-z_]+\.[a-z0-9_]{1,248}", entity) for entity in exclude):
        raise ValueError("Excluded entities must be HA entity ids")
    pages = options.get("pages", {})
    if not isinstance(pages, dict):
        raise TypeError("Page overrides must be an object")
    for override in pages.values():
        if not isinstance(override, dict) or set(override) - OVERRIDE_FIELDS:
            raise ValueError("Unknown Explorer page setting")
        if override.get("style", next(iter(NAV_STYLES))) not in NAV_STYLES:
            raise ValueError("Explorer pages use navigation styles")
        validate_options(override)


def read_home(hass) -> Home:
    """Take the home's structure from HA's registries, changing nothing."""
    from homeassistant.helpers import area_registry as ar
    from homeassistant.helpers import device_registry as dr
    from homeassistant.helpers import entity_registry as er
    from homeassistant.helpers import floor_registry as fr

    devices = dr.async_get(hass)
    home = Home(
        floors=[Floor(floor.floor_id, floor.name, floor.level, floor.icon) for floor in fr.async_get(hass).async_list_floors()],
        areas=[Area(area.id, area.name, area.floor_id, area.icon) for area in ar.async_get(hass).async_list_areas()],
    )
    registered = er.async_get(hass).entities
    for entry in registered.values():
        # At HA's start many entities have no state yet, so the registry decides what exists.
        state = hass.states.get(entry.entity_id)
        attributes = state.attributes if state else {}
        device = devices.async_get(entry.device_id) if entry.device_id else None
        category = entry.entity_category
        home.entities.append(
            Entity(
                entry.entity_id,
                attributes.get("friendly_name") or entry.name or entry.original_name or _from_id(entry.entity_id),
                entry.area_id or (device.area_id if device else None),
                entry.icon or attributes.get("icon") or entry.original_icon,
                entry.device_class or entry.original_device_class or attributes.get("device_class"),
                category.value if category else None,
                entry.hidden_by is not None,
                entry.disabled_by is not None,
                entry.options.get(ASSISTANT, {}).get("should_expose"),
            )
        )
    for state in hass.states.async_all():
        if state.entity_id not in registered:
            home.entities.append(_unregistered(hass, state))
    return home


def _unregistered(hass, state) -> Entity:
    """A YAML or helper entity, with no registry entry and so no area."""
    from homeassistant.components.homeassistant.exposed_entities import (
        async_get_entity_settings,
    )
    from homeassistant.exceptions import HomeAssistantError

    try:
        exposed = async_get_entity_settings(hass, state.entity_id).get(ASSISTANT, {}).get("should_expose")
    except HomeAssistantError:
        exposed = None
    attributes = state.attributes
    return Entity(
        state.entity_id,
        attributes.get("friendly_name") or _from_id(state.entity_id),
        icon=attributes.get("icon"),
        device_class=attributes.get("device_class"),
        exposed=exposed,
    )


def _from_id(entity_id: str) -> str:
    return entity_id.partition(".")[2].replace("_", " ").title()


def _natural(text: str) -> list:
    """So that Sensor 2 comes before Sensor 10. Split always alternates text and digits, so items compare."""
    return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", text.lower())]


def _short_id(prefix: str, value: str) -> str:
    """Item ids are limited to 64 characters, and HA's ids aren't."""
    text = f"{prefix}{value}"
    return text if len(text) <= 64 else f"{prefix}{sha256(value.encode()).hexdigest()[:32]}"


def _is_security(entity: Entity) -> bool:
    domain = entity.entity_id.partition(".")[0]
    return domain in SECURITY_DOMAINS or (domain == "cover" and entity.device_class in CONFIRMED_COVERS)


def _omitted_because(entity: Entity, options: dict) -> str | None:
    if entity.disabled:
        return "disabled"
    if entity.entity_id.partition(".")[0] not in CONTROL_TYPES:
        return "unsupported"
    if entity.hidden:
        return "hidden"
    if entity.category in HIDDEN_CATEGORIES:
        return "diagnostic"
    if entity.entity_id in options.get("exclude", []):
        return "excluded"
    if options.get("assist_only") and not entity.exposed:
        return "not_exposed"
    if not options.get("include_security", True) and _is_security(entity):
        return "security"
    return None


def _label(entity: Entity, area: Area | None) -> str:
    """A room's own name is wasted on a small screen when you're already in that room."""
    name = entity.name
    if area and name.lower().startswith(area.name.lower() + " "):
        name = name[len(area.name) + 1 :].strip()
        name = name[:1].upper() + name[1:]
    return (name or entity.name)[:64]


def _control(entity: Entity, area: Area | None) -> dict:
    domain = entity.entity_id.partition(".")[0]
    profile, style, icon = CONTROL_TYPES[domain]
    return {
        "id": _short_id("", entity.entity_id),
        "label": _label(entity, area),
        "icon": usable_icon(entity.icon, icon),
        "entity_id": entity.entity_id,
        "label_override": False,
        "profile": profile,
        "style": style,
        # Navigator already confirms these domains; a door is the case it can't know from the domain.
        **({"confirm": True} if _is_security(entity) else {}),
    }


def _menu(page_id: str, label: str, icon: str | None, items: list[dict], fallback: str = "mdi:folder") -> dict:
    return {"id": _short_id("x_", page_id), "label": label[:64], "icon": usable_icon(icon, fallback), "children": items}


def _function_of(entity: Entity) -> tuple:
    domain = entity.entity_id.partition(".")[0]
    return next((function for function in FUNCTIONS if domain in function[2]), OTHER)


def _room_items(page_id: str, entities: list[Entity], area: Area | None) -> list[dict]:
    """A room's entities directly, or grouped by function when there are too many to scan."""
    order = [*FUNCTIONS, OTHER]
    ranked = sorted(entities, key=lambda entity: (order.index(_function_of(entity)), _natural(_label(entity, area))))
    groups: dict[tuple, list[Entity]] = {}
    for entity in ranked:
        groups.setdefault(_function_of(entity)[:2], []).append(entity)
    if len(ranked) <= MAX_SHOWN or len(groups) == 1:
        return [_control(entity, area) for entity in ranked]
    items = []
    for (name, icon), members in groups.items():
        if len(members) == 1:
            items.append(_control(members[0], area))
        else:
            controls = sorted((_control(entity, area) for entity in members), key=lambda item: _natural(item["label"]))
            items.append(_menu(f"{page_id}_{name.lower()}", name, icon, controls))
    return items


def _area_menu(area: Area, by_area: dict) -> dict | None:
    entities = by_area.get(area.id)
    return _menu(f"area_{area.id}", area.name, area.icon, _room_items(f"area_{area.id}", entities, area), "mdi:floor-plan") if entities else None


def _floor_key(floor: Floor) -> tuple:
    # HA has no fixed rule for a floor without a level, so those follow the levelled ones by name.
    return (floor.level is None, -(floor.level or 0), floor.name.lower())


def _generated_items(home: Home, shown: list[Entity], options: dict) -> list[dict]:
    known = {area.id: area for area in home.areas}
    by_area: dict[str | None, list[Entity]] = {}
    for entity in shown:
        by_area.setdefault(entity.area_id if entity.area_id in known else None, []).append(entity)
    areas = sorted(home.areas, key=lambda area: _natural(area.name))

    if area_id := options.get("area_id"):
        return _room_items(f"area_{area_id}", by_area.get(area_id, []), known.get(area_id))
    if floor_id := options.get("floor_id"):
        return [menu for area in areas if area.floor_id == floor_id and (menu := _area_menu(area, by_area))]

    floors = {floor.id: floor for floor in home.floors}
    floor_menus = []
    for floor in sorted(home.floors, key=_floor_key):
        menus = [menu for area in areas if area.floor_id == floor.id and (menu := _area_menu(area, by_area))]
        if menus:
            floor_menus.append((floor, menus))
    loose = [menu for area in areas if area.floor_id not in floors and (menu := _area_menu(area, by_area))]
    # One floor says nothing, so its areas move up a level.
    if len(floor_menus) == 1:
        loose, floor_menus = [*floor_menus[0][1], *loose], []
    items = [_menu(f"floor_{floor.id}", floor.name, floor.icon, menus, FLOOR_ICONS.get(floor.level, "mdi:layers")) for floor, menus in floor_menus]
    items += loose
    if unassigned := by_area.get(None):
        items.append(_menu("other", "Other devices", "mdi:devices", _room_items("other", unassigned, None)))
    return items


def _shuffled(key: str, count: int, options: dict) -> str:
    """The same page keeps the same style, so a rebuild doesn't redecorate the home; Shuffle changes it."""
    pool = sorted(NAV_STYLES if count <= MAX_SHOWN else PAGED_STYLES)
    return pool[int(sha256(f"{options.get('shuffle', 0)}:{key}".encode()).hexdigest(), 16) % len(pool)]


def page_style(key: str, count: int, default: str, options: dict) -> str:
    """Any navigation style while the items fit; a page that outgrows its style falls back rather than hiding some."""
    override = options.get("pages", {}).get(key, {}).get("style")
    style = override or (_shuffled(key, count, options) if options.get("random") else default)
    if style not in NAV_STYLES:
        style = DEFAULT_LONG_STYLE
    if count > MAX_SHOWN and style not in PAGED_STYLES:
        return options.get("long_style", DEFAULT_LONG_STYLE)
    return style


def _dress(items: list[dict], parent: dict, options: dict) -> None:
    """Give each generated page its style, then whatever its own override says."""
    for item in items:
        if "children" not in item:
            if item["entity_id"].partition(".")[0] in PICTURE_DOMAINS:
                item["style"] = options.get("camera_style", item["style"])
                # Left out, each camera style keeps its own default treatment.
                if "picture_mode" in options:
                    item["appearance"] = {"picture-mode": options["picture_mode"]}
            continue
        override = options.get("pages", {}).get(item["id"], {})
        item["style"] = page_style(item["id"], len(item["children"]), parent["style"], options)
        item["theme"] = override.get("theme", parent["theme"])
        if "icon" in override:
            item["icon"] = usable_icon(override["icon"], item["icon"])
        for key in ("appearance", "css"):
            if key in override:
                item[key] = override[key]
            elif key in parent:
                item[key] = parent[key]
        # Descendants inherit from the Explorer, not from a sibling's override.
        _dress(item["children"], parent, options)


def explore(home: Home, options: dict, base: dict) -> tuple[list[dict], dict]:
    """The generated items and what was left out of them. `base` is the Explorer's own style settings."""
    shown, omitted = [], {}
    for entity in home.entities:
        reason = _omitted_because(entity, options)
        if reason:
            omitted[reason] = omitted.get(reason, 0) + 1
        else:
            shown.append(entity)
    items = _generated_items(home, shown, options)
    _dress(items, base, options)
    placed = sum(1 for _ in _controls(items))
    if len(shown) > placed:
        omitted["out_of_scope"] = len(shown) - placed
    return items, {"shown": placed, "omitted": omitted}


def _controls(items: list[dict]):
    for item in items:
        if "children" in item:
            yield from _controls(item["children"])
        else:
            yield item


def outline(items: list[dict]) -> list[dict]:
    """What the panel shows of a generated tree, without the rendering details."""
    return [
        {"id": item["id"], "label": item["label"], **({"style": item["style"], "children": outline(item["children"])} if "children" in item else {"entity_id": item["entity_id"]})}
        for item in items
    ]
