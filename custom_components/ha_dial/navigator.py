"""The HA-owned current-screen model."""

from __future__ import annotations

from copy import deepcopy


class Navigator:
    def __init__(self, light_entity: str | None = None, light_name: str = "Light") -> None:
        items = []
        if light_entity:
            items.append(
                {
                    "id": light_entity,
                    "label": light_name,
                    "icon": "mdi:lightbulb",
                    "entity_id": light_entity,
                    "profile": "dimmer",
                }
            )
        self.views = {
            "root": {
                "id": "root",
                "title": "Home",
                "items": [
                    {
                        "id": "lights",
                        "label": "Lights",
                        "icon": "mdi:lightbulb",
                        "view": "lights",
                    }
                ],
            },
            "lights": {
                "id": "lights",
                "title": "Lights",
                "parent": "root",
                "items": items,
            },
        }
        self.view_id = "root"
        self.selected = 0
        self.control: dict | None = None

    def current(self) -> dict:
        if self.control is not None:
            return deepcopy(self.control)
        view = deepcopy(self.views[self.view_id])
        view.update(kind="menu", selected=self.selected, back="parent" in view)
        return view

    def input(
        self, action: str, item_id: str | None = None, value: float | None = None
    ) -> dict:
        if action == "ready":
            return self.current()
        if action == "back":
            self._back()
            return self.current()
        if self.control is not None:
            if not self.control["available"]:
                return self.current()
            if action in {"rotate_left", "rotate_right"}:
                direction = -1 if action == "rotate_left" else 1
                value = self.control["value"] + direction * self.control["step"]
                value = max(self.control["minimum"], min(self.control["maximum"], value))
                self.control["value"] = round(value, 2)
                self.control["active"] = True
            elif action == "set_value" and value is not None:
                value = max(self.control["minimum"], min(self.control["maximum"], value))
                self.control["value"] = round(value, 2)
                self.control["active"] = True
            elif action == "press":
                self.control["active"] = not self.control["active"]
            return self.current()

        items = self.views[self.view_id]["items"]
        if action in {"rotate_left", "rotate_right"} and items:
            step = -1 if action == "rotate_left" else 1
            self.selected = (self.selected + step) % len(items)
        elif action == "touch" and item_id is not None:
            match = next((index for index, item in enumerate(items) if item["id"] == item_id), None)
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
            self.control = {
                "kind": "control",
                "id": f"control:{entity_id}",
                "title": item["label"],
                "icon": item["icon"],
                "entity_id": entity_id,
                "profile": item["profile"],
                "value": 50,
                "minimum": 0,
                "maximum": 100,
                "step": 5,
                "unit": "%",
                "active": True,
                "available": True,
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
            self.view_id, self.selected = parent, 0

    def sync(
        self, value: int, active: bool, available: bool, title: str | None = None
    ) -> None:
        if self.control is not None:
            self.control.update(value=value, active=active, available=available)
            if title:
                self.control["title"] = title
