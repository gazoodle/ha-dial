"""Validation for the user-authored page tree sent by the Lovelace card."""

from __future__ import annotations

THEMES = {"ember", "verdant", "cobalt", "rose", "acid", "alloy"}
CONTROL_TYPES = {
    "light": ("dimmer", "CTL-LIGHT-INSTRUMENT", "mdi:lightbulb"),
    "switch": ("toggle", "CTL-SWITCH-INSTRUMENT", "mdi:toggle-switch"),
    "cover": ("position", "CTL-COVER-INSTRUMENT", "mdi:blinds"),
}
STYLES = {"NAV-ORBIT", *(value[1] for value in CONTROL_TYPES.values())}


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

    roots = [page for page in by_id.values() if not page.get("parent")]
    if len(roots) != 1:
        raise ValueError(
            "The page tree needs exactly one root (leave its parent empty)"
        )

    def make_page(page: dict, ancestors: frozenset[str]) -> dict:
        page_id = page["id"]
        if page_id in ancestors:
            raise ValueError("Page parent links cannot contain a cycle")
        children = [item for item in by_id.values() if item.get("parent") == page_id]
        items = [
            {
                "id": child["id"],
                "label": child["title"],
                "theme": child["theme"],
                "style": "NAV-ORBIT",
                "icon": child.get("icon", "mdi:folder"),
                "children": make_page(child, ancestors | {page_id})["items"],
            }
            for child in children
        ]
        for entity_id in page["lights"]:
            if (
                not isinstance(entity_id, str)
                or entity_id.partition(".")[0] not in CONTROL_TYPES
                or not entity_id.partition(".")[2]
            ):
                raise ValueError(
                    f"Page {page_id} must select light, switch or cover entities"
                )
            profile, style, icon = CONTROL_TYPES[entity_id.partition(".")[0]]
            state = hass.states.get(entity_id)
            label = state.attributes.get("friendly_name") if state else None
            items.append(
                {
                    "id": entity_id,
                    "label": label
                    or entity_id.split(".", 1)[1].replace("_", " ").title(),
                    "icon": state.attributes.get("icon", icon) if state else icon,
                    "entity_id": entity_id,
                    "profile": profile,
                    "style": style,
                }
            )
        if len(items) > 8:
            raise ValueError(f"Page {page_id} can show at most 8 items")
        return {
            "id": page_id,
            "title": page["title"],
            "theme": page["theme"],
            "style": "NAV-ORBIT",
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
        if page.get("style", "NAV-ORBIT") != "NAV-ORBIT":
            raise ValueError("Navigation pages must use NAV-ORBIT")
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
            if item["id"] in {"back", "home", "control"}:
                raise ValueError("Item ids back, home and control are reserved")
            if (
                not isinstance(item.get("label"), str)
                or not item["label"]
                or len(item["label"]) > 64
            ):
                raise ValueError("Each item needs a label of at most 64 characters")
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
                if item.get("style", "NAV-ORBIT") != "NAV-ORBIT":
                    raise ValueError("Nested pages must use NAV-ORBIT")
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
                if item.get("style", style) != style:
                    raise ValueError(f"{domain.title()} controls must use {style}")

    check_page(tree)


def leaf_items(tree: dict):
    for item in tree.get("items", []):
        if "children" in item:
            yield from leaf_items({"items": item["children"]})
        else:
            yield item
