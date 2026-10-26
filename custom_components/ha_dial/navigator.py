"""The HA-owned current-screen model."""

from __future__ import annotations

from copy import deepcopy

VIEWS = {
    "root": {
        "id": "root",
        "title": "Home",
        "items": [
            {"id": "lights", "label": "Lights", "icon": "mdi:lightbulb", "view": "lights"},
            {
                "id": "heating",
                "label": "Heating",
                "icon": "mdi:thermostat",
                "entity_id": "climate.example",
                "profile": "thermostat",
            },
            {
                "id": "music",
                "label": "Music",
                "icon": "mdi:speaker",
                "entity_id": "media_player.example",
                "profile": "volume",
            },
        ],
    },
    "lights": {
        "id": "lights",
        "title": "Lights",
        "parent": "root",
        "items": [
            {
                "id": "kitchen",
                "label": "Kitchen",
                "icon": "mdi:ceiling-light",
                "entity_id": "light.example_kitchen",
                "profile": "dimmer",
            },
            {
                "id": "hall",
                "label": "Hall",
                "icon": "mdi:wall-sconce-flat",
                "entity_id": "light.example_hall",
                "profile": "dimmer",
            },
        ],
    },
}

CONTROL_DEFAULTS = {
    "dimmer": {"value": 50, "minimum": 0, "maximum": 100, "step": 5, "unit": "%"},
    "thermostat": {"value": 20, "minimum": 7, "maximum": 30, "step": 0.5, "unit": "°C"},
    "volume": {"value": 40, "minimum": 0, "maximum": 100, "step": 5, "unit": "%"},
}


class Navigator:
    def __init__(self) -> None:
        self.view_id = "root"
        self.selected = 0
        self.control: dict | None = None

    def current(self) -> dict:
        if self.control is not None:
            return deepcopy(self.control)
        view = deepcopy(VIEWS[self.view_id])
        view.update(kind="menu", selected=self.selected, back="parent" in view)
        return view

    def input(self, action: str, item_id: str | None = None) -> dict:
        if action == "ready":
            return self.current()
        if action == "back":
            self._back()
            return self.current()
        if self.control is not None:
            if action in {"rotate_left", "rotate_right"}:
                direction = -1 if action == "rotate_left" else 1
                value = self.control["value"] + direction * self.control["step"]
                value = max(self.control["minimum"], min(self.control["maximum"], value))
                self.control["value"] = round(value, 2)
            elif action == "press":
                self.control["active"] = not self.control["active"]
            return self.current()

        items = VIEWS[self.view_id]["items"]
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
                **CONTROL_DEFAULTS[item["profile"]],
                "active": True,
                "back": True,
                "items": [],
                "selected": 0,
            }

    def _back(self) -> None:
        if self.control is not None:
            self.control = None
            return
        view = VIEWS[self.view_id]
        if parent := view.get("parent"):
            self.view_id, self.selected = parent, 0
