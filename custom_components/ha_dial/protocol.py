"""Bounded device transport for an already resolved scene."""

import json

from .scene import MAX_VIEW_BYTES, compile_scene


def device_payload(
    view: dict, previous: dict | None, revision: int, input_sequence: int = 0
) -> str:
    payload = {
        "revision": revision,
        "input_sequence": input_sequence,
        "scene": compile_scene(view),
        "back": bool(previous),
        "settings": view.get("kind") == "settings",
    }
    if previous:
        payload["previous"] = compile_scene(previous)
    if view.get("kind") == "control" and view.get("continuous", True):
        payload.update(
            {
                key: view[key]
                for key in (
                    "value",
                    "minimum",
                    "maximum",
                    "step",
                    "available",
                    "pending",
                )
            }
        )
    encoded = json.dumps(payload, separators=(",", ":"), ensure_ascii=True)
    if len(encoded.encode()) > MAX_VIEW_BYTES:
        raise ValueError(f"Resolved scene exceeds {MAX_VIEW_BYTES} bytes")
    return encoded
