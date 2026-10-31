"""The HA-owned current-screen model."""

from __future__ import annotations

import json
import math
from copy import deepcopy
from hashlib import sha256

from .definition import CONTROL_TYPES


class Navigator:
    def __init__(
        self,
        light_entity: str | None = None,
        light_name: str = "Light",
        definition: dict | None = None,
    ) -> None:
        root = (definition or {}).get("tree")
        if not isinstance(root, dict):
            root = {
                "id": "root",
                "title": "Home",
                "theme": "ember",
                "style": "NAV-ORBIT",
                "items": [
                    {
                        "id": "lights",
                        "label": "Lights",
                        "icon": "mdi:lightbulb",
                        "children": (
                            [
                                {
                                    "id": light_entity,
                                    "label": light_name,
                                    "icon": "mdi:lightbulb",
                                    "entity_id": light_entity,
                                    "profile": "dimmer",
                                    "style": "CTL-LIGHT-INSTRUMENT",
                                }
                            ]
                            if light_entity
                            else []
                        ),
                    }
                ],
            }
        self.views: dict[str, dict] = {}

        def add_page(node: dict, parent: str | None = None, path: tuple = ()) -> str:
            path = (*path, node.get("id", "root"))
            page_id = (
                node.get("id", "root")
                if parent is None
                else "page:" + sha256(json.dumps(path).encode()).hexdigest()[:24]
            )
            items = []
            for index, child in enumerate(node.get("items", [])):
                item = {
                    key: child[key]
                    for key in (
                        "id",
                        "label",
                        "icon",
                        "entity_id",
                        "profile",
                        "style",
                        "theme",
                        "appearance",
                        "css",
                        "confirm",
                        "label_override",
                        "clock",
                        "action_items",
                    )
                    if key in child
                }
                if isinstance(child.get("children"), list):
                    item["view"] = add_page(
                        {
                            "id": child["id"],
                            "title": item.get("label", "Menu"),
                            "theme": child.get("theme", node.get("theme", "ember")),
                            "style": child.get("style", node.get("style", "NAV-ORBIT")),
                            **{
                                key: child[key]
                                for key in ("appearance", "css", "clock")
                                if key in child
                            },
                            "items": child["children"],
                        },
                        page_id,
                        path,
                    )
                items.append(item)
            self.views[page_id] = {
                "id": page_id,
                "title": str(node.get("title", "Home"))[:24],
                "theme": node.get("theme", "ember"),
                "style": node.get("style", "NAV-ORBIT"),
                **{key: node[key] for key in ("appearance", "css", "clock") if key in node},
                "parent": parent,
                "items": items,
            }
            return page_id

        self.settings_enabled = False
        self.root_id = add_page(root)
        for page in self.views.values():
            ancestors = []
            parent = page.get("parent")
            while parent:
                ancestors.insert(0, self.views[parent]["title"])
                parent = self.views[parent].get("parent")
            page["breadcrumbs"] = ancestors
        self.view_id = self.root_id
        self.selected = 0
        self.control: dict | None = None
        # The camera a control was opened from, so that Back returns to it and not to the page.
        self.control_parent: dict | None = None
        self.clock_snapshot: dict | None = None

    def _items(self, page_id=None):
        page_id = page_id or self.view_id
        items = self.views[page_id]["items"]
        if self.settings_enabled and page_id == self.root_id:
            return [
                *items,
                {
                    "id": "__settings",
                    "label": "Settings",
                    "icon": "mdi:cog",
                    "settings": True,
                },
            ]
        return items

    def current(self) -> dict:
        if self.control is not None:
            return deepcopy(self.control)
        view = deepcopy(self.views[self.view_id])
        view["items"] = self._items()
        view.update(
            kind="menu",
            selected=self.selected % max(1, len(view["items"])),
            back=bool(view.get("parent")),
        )
        return view

    def previous(self) -> dict | None:
        if self.control_parent is not None:
            return deepcopy(self.control_parent)
        page = deepcopy(self.views[self.view_id])
        page["items"] = self._items()
        if self.control is not None:
            page.update(
                kind="menu", selected=self.selected, back=bool(page.get("parent"))
            )
            return page
        if parent := page.get("parent"):
            page = deepcopy(self.views[parent])
            page.update(
                kind="menu",
                selected=next(
                    (
                        i
                        for i, item in enumerate(page["items"])
                        if item.get("view") == self.view_id
                    ),
                    0,
                ),
                back=bool(page.get("parent")),
            )
            return page
        return None

    def input(
        self, action: str, item_id: str | None = None, value: float | None = None
    ) -> dict:
        if self.control is not None:
            self.control.pop("_confirmed", None)
        if action == "ready":
            return self.current()
        if action == "home":
            self.control = None
            self.control_parent = None
            self.view_id, self.selected = self.root_id, 0
            return self.current()
        if action == "back":
            self._back()
            return self.current()
        if self.control is not None:
            if self.control.get("kind") == "settings":
                if action in {"press", "rotate_left", "rotate_right", "touch"}:
                    self.control = None
                return self.current()
            if self.control.get("items"):
                return self._camera_input(action, item_id)
            if not self.control["available"]:
                return self.current()
            if self.control.get("confirmation"):
                if (
                    action == "touch"
                    and item_id == "cancel"
                    or action in {"rotate_left", "rotate_right"}
                ):
                    self.control.pop("confirmation", None)
                    return self.current()
                if action == "press" or action == "touch" and item_id == "confirm":
                    self.control["_confirmed"] = self.control["confirmation"]
                    if self.control.get("domain") in {"light", "switch"}:
                        self.control["active"] = not self.control["active"]
                    self.control.pop("confirmation", None)
                    self.control["pending"] = True
                    return self.current()
                return self.current()
            command = (
                item_id
                if action == "touch"
                else "toggle"
                if self.control.get("domain") in {"light", "switch"}
                else "stop"
                if self.control.get("domain") == "cover"
                and "stop" in self.control.get("actions", [])
                else (self.control.get("actions") or [None])[0]
            )
            if (
                command is not None
                and self.control.get("confirm")
                and (
                    action == "press"
                    or action == "touch"
                    and command in self.control.get("actions", [])
                )
            ):
                self.control["confirmation"] = command
                return self.current()
            if action in {
                "rotate_left",
                "rotate_right",
                "set_value",
            } and not self.control.get("continuous", True):
                return self.current()
            if action == "touch" and item_id in self.control.get("actions", []):
                self.control.pop("target_value", None)
                self.control["pending"] = True
            elif action in {"rotate_left", "rotate_right"}:
                direction = -1 if action == "rotate_left" else 1
                adjusted = float(self.control["value"]) + direction * float(
                    self.control["step"]
                )
                adjusted = max(
                    self.control["minimum"], min(self.control["maximum"], adjusted)
                )
                self.control["value"] = round(adjusted, 2)
                self.control["target_value"] = self.control["value"]
                self.control["active"] = True
                self.control["pending"] = True
            elif action == "set_value" and value is not None:
                if not math.isfinite(value):
                    return self.current()
                value = max(
                    self.control["minimum"], min(self.control["maximum"], value)
                )
                self.control["value"] = round(value, 2)
                self.control["target_value"] = self.control["value"]
                self.control["active"] = True
                self.control["pending"] = True
            elif action == "press":
                if self.control.get("domain") not in {
                    "light",
                    "switch",
                    "cover",
                } and not self.control.get("actions"):
                    return self.current()
                self.control.pop("target_value", None)
                if self.control["profile"] == "position":
                    if "stop" in self.control.get("actions", []):
                        self.control["pending"] = True
                else:
                    self.control["active"] = not self.control["active"]
                    self.control["pending"] = True
            return self.current()

        items = self._items()
        if action in {"rotate_left", "rotate_right"} and items:
            step = -1 if action == "rotate_left" else 1
            self.selected = (self.selected + step) % len(items)
        elif action == "touch" and item_id is not None:
            match = next(
                (index for index, item in enumerate(items) if item["id"] == item_id),
                None,
            )
            if match is not None:
                self.selected = match
                self._activate(items[match])
        elif action == "press" and items:
            self._activate(items[self.selected])
        return self.current()

    def _camera_input(self, action: str, item_id: str | None) -> dict:
        """A camera's buttons work like a menu: turn to choose, press to open that control."""
        items = self.control["items"]
        if action in {"rotate_left", "rotate_right"}:
            step = -1 if action == "rotate_left" else 1
            self.control["selected"] = (self.control.get("selected", 0) + step) % len(items)
            return self.current()
        if action == "press":
            target = items[self.control.get("selected", 0) % len(items)]
        elif action == "touch":
            target = next((item for item in items if item["id"] == item_id), None)
        else:
            target = None
        if target is not None:
            parent = self.control
            self._activate(target)
            self.control_parent = parent
        return self.current()

    def _activate(self, item: dict) -> None:
        if item.get("settings"):
            self.control = {
                "id": "settings",
                "kind": "settings",
                "domain": "settings",
                "title": "Device settings",
                "icon": "mdi:cog",
                "style": "CTL-SETTINGS-EDITORIAL",
                "available": True,
                "state": "Local diagnostics",
                "detail": "Shown locally on the Dial",
                "value": 0,
                "continuous": False,
                "back": True,
                "actions": [],
            }
            return
        if target := item.get("view"):
            self.view_id, self.selected = target, 0
            return
        if entity_id := item.get("entity_id"):
            domain = entity_id.partition(".")[0]
            profile, style, icon = CONTROL_TYPES[domain]
            self.control = {
                **{
                    key: item[key]
                    for key in ("appearance", "css", "confirm", "label_override", "clock")
                    if key in item
                },
                "appearance": {
                    **self.views[self.view_id].get("appearance", {}),
                    **item.get("appearance", {}),
                },
                "css": self.views[self.view_id].get("css", "")
                + ";"
                + item.get("css", ""),
                "confirm": item.get(
                    "confirm",
                    domain
                    in {
                        "lock",
                        "alarm_control_panel",
                        "scene",
                        "button",
                        "input_button",
                    },
                ),
                "kind": "control",
                "id": f"control:{entity_id}",
                "title": item["label"],
                "icon": item.get("icon", icon),
                "entity_id": entity_id,
                "profile": item.get("profile", profile),
                "theme": item.get(
                    "theme", self.views[self.view_id].get("theme", "ember")
                ),
                "style": item.get("style", style),
                "domain": domain,
                "continuous": domain == "light",
                "actions": [],
                "value": 50,
                "minimum": 0,
                "maximum": 100,
                "step": 5,
                "unit": "%",
                "active": True,
                "available": True,
                "pending": False,
                "back": True,
                "items": item.get("action_items", []),
                "selected": 0,
            }

    def _back(self) -> None:
        if self.control is not None:
            self.control, self.control_parent = self.control_parent, None
            return
        view = self.views[self.view_id]
        if parent := view.get("parent"):
            previous_id = self.view_id
            self.view_id = parent
            self.selected = next(
                (
                    i
                    for i, item in enumerate(self.views[parent]["items"])
                    if item.get("view") == previous_id
                ),
                0,
            )

    def restore(self, previous: Navigator) -> None:
        target = previous.view_id
        while target not in self.views:
            target = previous.views.get(target, {}).get("parent")
            if target is None:
                return
        self.view_id = target
        items = self.views[self.view_id]["items"]
        self.selected = previous.selected % max(1, len(items))
        if previous.control is not None:
            for index, item in enumerate(items):
                if item.get("entity_id") == previous.control["entity_id"]:
                    self.selected = index
                    self._activate(item)
                    break

    def sync(
        self,
        value: int,
        active: bool,
        available: bool,
        title: str | None = None,
        **properties,
    ) -> None:
        if self.control is not None:
            target = self.control.get("target_value")
            pending = (
                target is not None
                and available
                and properties.get("continuous", True)
                and abs(value - target) >= 0.5
            )
            if not pending:
                self.control.pop("target_value", None)
            self.control.update(
                confirmed_value=value,
                value=target if pending else value,
                active=active,
                available=available,
                pending=pending,
                **properties,
            )
            if title and not self.control.get("label_override"):
                self.control["title"] = title
