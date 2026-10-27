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
                "parent": parent,
                "items": items,
            }
            return page_id

        self.root_id = add_page(root)
        self.view_id = self.root_id
        self.selected = 0
        self.control: dict | None = None

    def current(self) -> dict:
        if self.control is not None:
            return deepcopy(self.control)
        view = deepcopy(self.views[self.view_id])
        view.update(kind="menu", selected=self.selected, back=bool(view.get("parent")))
        return view

    def previous(self) -> dict | None:
        page = deepcopy(self.views[self.view_id])
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
        if action == "ready":
            return self.current()
        if action == "home":
            self.control = None
            self.view_id, self.selected = self.root_id, 0
            return self.current()
        if action == "back":
            self._back()
            return self.current()
        if self.control is not None:
            if not self.control["available"]:
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
                self.control.pop("target_value", None)
                if self.control["profile"] == "position":
                    if "stop" in self.control.get("actions", []):
                        self.control["pending"] = True
                else:
                    self.control["active"] = not self.control["active"]
                    self.control["pending"] = True
            return self.current()

        items = self.views[self.view_id]["items"]
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

    def _activate(self, item: dict) -> None:
        if target := item.get("view"):
            self.view_id, self.selected = target, 0
            return
        if entity_id := item.get("entity_id"):
            domain = entity_id.partition(".")[0]
            profile, style, icon = CONTROL_TYPES[domain]
            self.control = {
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
                "items": [],
                "selected": 0,
            }

    def _back(self) -> None:
        if self.control is not None:
            self.control = None
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
        if previous.view_id not in self.views:
            return
        self.view_id = previous.view_id
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
            if title:
                self.control["title"] = title
