"""Validation for the user-authored page tree sent by the Lovelace card."""

from __future__ import annotations

THEMES = {"ember", "verdant", "cobalt", "rose", "acid", "alloy"}
from .appearance import validate_options
from .assets import usable_icon
from .catalogue import CONTROL_TYPES, PAGE_STYLES, STYLES, control_styles


def build_definition(hass, pages: list, default_theme: str) -> dict:
    if not isinstance(pages, list) or not pages:
        raise ValueError("Add at least one page")
    by_id = {}
    for page in pages:
        if not isinstance(page, dict):
            raise TypeError("Each page must be an object")
        page_id, title = page.get("id"), page.get("title")
        if not isinstance(page_id, str) or not page_id or len(page_id) > 64:
            raise ValueError("Each page needs an id of at most 64 characters")
        if page_id in by_id:
            raise ValueError("Page ids must be unique")
        if not isinstance(title, str) or not title or len(title) > 64:
            raise ValueError("Each page needs a title of at most 64 characters")
        validate_options(page)
        theme = page.get("theme", default_theme)
        if theme not in THEMES:
            raise ValueError(f"Unknown theme on page {page_id}")
        if any(
            not isinstance(page.get(key, []), list) for key in ("lights", "entities")
        ):
            raise ValueError("Page controls must be lists")
        lights = [*page.get("lights", []), *page.get("entities", [])]
        if not isinstance(lights, list) or len(lights) > 8:
            raise ValueError(f"Page {page_id} can select at most 8 controls")
        by_id[page_id] = {**page, "theme": theme, "lights": lights}

    children_by_parent = {}
    for page in by_id.values():
        children_by_parent.setdefault(page.get("parent"), []).append(page)
    roots = [page for page in by_id.values() if not page.get("parent")]
    if len(roots) != 1:
        raise ValueError(
            "The page tree needs exactly one root (leave its parent empty)"
        )

    def make_page(page: dict, ancestors: frozenset[str]) -> dict:
        page_id = page["id"]
        if page_id in ancestors:
            raise ValueError("Page parent links cannot contain a cycle")
        children = children_by_parent.get(page_id, [])
        items = [
            {
                "id": child["id"],
                "label": child["title"],
                "theme": child["theme"],
                "style": child.get("style", "NAV-ORBIT"),
                **{
                    key: child[key]
                    for key in ("appearance", "css", "conditions", "clock")
                    if key in child
                },
                "icon": child.get("icon", "mdi:folder"),
                "children": make_page(child, ancestors | {page_id})["items"],
            }
            for child in children
        ]
        for entity in page["lights"]:
            options = entity if isinstance(entity, dict) else {"entity_id": entity}
            entity_id = options.get("entity_id")
            validate_options(options)
            if (
                not isinstance(entity_id, str)
                or entity_id.partition(".")[0] not in CONTROL_TYPES
                or not entity_id.partition(".")[2]
            ):
                raise ValueError(f"Page {page_id} must select a supported HA entity")
            profile, style, icon = CONTROL_TYPES[entity_id.partition(".")[0]]
            state = hass.states.get(entity_id)
            action_items = [_action_item(hass, action) for action in options.get("clock", {}).get("action_entities", [])]
            label = state.attributes.get("friendly_name") if state else None
            items.append(
                {
                    **options,
                    "id": options.get("id", entity_id),
                    "label": options.get("label")
                    or label
                    or entity_id.split(".", 1)[1].replace("_", " ").title(),
                    "icon": options.get("icon")
                    or (usable_icon(state.attributes.get("icon"), icon) if state else icon),
                    "entity_id": entity_id,
                    "label_override": bool(options.get("label")),
                    "profile": profile,
                    "style": options.get("style", style),
                    **({"action_items": action_items} if action_items else {}),
                }
            )
        if len(items) > 8:
            raise ValueError(f"Page {page_id} can show at most 8 items")
        return {
            "id": page_id,
            "title": page["title"],
            "theme": page["theme"],
            "style": page.get("style", "NAV-ORBIT"),
            **{
                key: page[key]
                for key in ("appearance", "css", "conditions", "clock")
                if key in page
            },
            "items": items,
        }

    for page in by_id.values():
        if page.get("parent") and page["parent"] not in by_id:
            raise ValueError(f"Unknown parent page {page['parent']}")
    definition = {"tree": make_page(roots[0], frozenset())}
    validate_definition(definition)
    if sum(1 for _ in _page_ids(definition["tree"])) != len(pages):
        raise ValueError("Every page must connect to the root")
    return definition


def _action_item(hass, entity_id: str) -> dict:
    """A camera's action button: the same item a page would hold, so it opens the same control."""
    domain = entity_id.partition(".")[0]
    if domain not in CONTROL_TYPES or domain in {"camera", "image"}:
        raise ValueError(f"A camera can't use {entity_id} as an action")
    profile, style, icon = CONTROL_TYPES[domain]
    state = hass.states.get(entity_id)
    return {
        "id": entity_id,
        "label": (state.attributes.get("friendly_name") if state else None) or entity_id.split(".", 1)[1].replace("_", " ").title(),
        "icon": usable_icon(state.attributes.get("icon"), icon) if state else icon,
        "entity_id": entity_id,
        "profile": profile,
        "style": style,
    }


def _page_ids(page: dict):
    yield page["id"]
    for item in page.get("items", []):
        if "children" in item:
            yield from _page_ids({"id": item["id"], "items": item["children"]})


def validate_definition(definition: dict) -> None:
    if not isinstance(definition, dict):
        raise TypeError("Definition must be an object")
    tree = definition.get("tree")
    if not isinstance(tree, dict):
        raise TypeError("Template must return an object with a tree")
    if not isinstance(tree.get("id"), str) or not tree["id"] or len(tree["id"]) > 64:
        raise ValueError("Root page needs a stable id of at most 64 characters")
    if (
        not isinstance(tree.get("title"), str)
        or not tree["title"]
        or len(tree["title"]) > 64
    ):
        raise ValueError("Root page needs a title of at most 64 characters")

    def check_page(page: dict) -> None:
        if page.get("theme", "ember") not in THEMES:
            raise ValueError("Unknown page theme")
        validate_options(page)
        if page.get("style", "NAV-ORBIT") not in PAGE_STYLES:
            raise ValueError("Unknown navigation style")
        items = page.get("items", [])
        if not isinstance(items, list) or len(items) > 8:
            raise ValueError("Each page must have at most 8 items")
        ids: set[str] = set()
        for item in items:
            if not isinstance(item, dict):
                raise TypeError("Each page item must be an object")
            if (
                not isinstance(item.get("id"), str)
                or not item["id"]
                or len(item["id"]) > 64
            ):
                raise ValueError("Each item needs a stable id of at most 64 characters")
            if item["id"] in ids:
                raise ValueError("Item ids must be unique within each page")
            ids.add(item["id"])
            if item["id"] in {"back", "home", "control", "__settings"}:
                raise ValueError(
                    "Item ids back, home, control and __settings are reserved"
                )
            if (
                not isinstance(item.get("label"), str)
                or not item["label"]
                or len(item["label"]) > 64
            ):
                raise ValueError("Each item needs a label of at most 64 characters")
            validate_options(item)
            children = item.get("children")
            default_style = (
                "NAV-ORBIT" if children is not None else "CTL-LIGHT-INSTRUMENT"
            )
            if item.get("style", default_style) not in STYLES:
                raise ValueError("Unknown item style")
            if item.get("theme", page.get("theme", "ember")) not in THEMES:
                raise ValueError("Unknown item theme")
            if children is not None:
                if not isinstance(children, list):
                    raise ValueError("Item children must be a list")
                if item.get("entity_id"):
                    raise ValueError("An item cannot be both a menu and a control")
                if item.get("style", "NAV-ORBIT") not in PAGE_STYLES:
                    raise ValueError("Unknown navigation style")
                check_page(
                    {
                        "items": children,
                        "theme": item.get("theme", page.get("theme", "ember")),
                        "style": item.get("style", page.get("style", "NAV-ORBIT")),
                    },
                )
            else:
                entity = item.get("entity_id")
                if (
                    not isinstance(entity, str)
                    or len(entity) > 255
                    or not entity.partition(".")[2]
                ):
                    raise ValueError(
                        "Leaf items must select a light, switch or cover entity"
                    )
                domain = entity.partition(".")[0]
                if domain not in CONTROL_TYPES:
                    raise ValueError(
                        "Leaf items must select a light, switch or cover entity"
                    )
                profile, style, _icon = CONTROL_TYPES[domain]
                if item.get("profile", profile) != profile:
                    raise ValueError(
                        f"{domain.title()} controls must use the {profile} profile"
                    )
                if item.get("style", style) not in control_styles(domain):
                    raise ValueError(f"{domain.title()} controls must use {style}")

    check_page(tree)


def leaf_items(tree: dict):
    for item in tree.get("items", []):
        if "children" in item:
            yield from leaf_items({"items": item["children"]})
        else:
            yield item
