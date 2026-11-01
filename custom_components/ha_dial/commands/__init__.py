"""The integration's websocket commands."""

from .common import DEVICE_RE, INPUTS
from .dial import (
    _ws_browse,
    _ws_configure,
    _ws_input,
    _ws_reset,
    _ws_subscribe,
    _ws_view,
)
from .editor import (
    _ws_condition_template,
    _ws_definitions,
    _ws_explorer,
    _ws_gallery,
)

COMMANDS = (
    _ws_view,
    _ws_input,
    _ws_configure,
    _ws_reset,
    _ws_subscribe,
    _ws_definitions,
    _ws_gallery,
    _ws_explorer,
    _ws_browse,
    _ws_condition_template,
)

__all__ = [
    "COMMANDS",
    "DEVICE_RE",
    "INPUTS",
    "_ws_browse",
    "_ws_condition_template",
    "_ws_configure",
    "_ws_definitions",
    "_ws_explorer",
    "_ws_gallery",
    "_ws_input",
    "_ws_reset",
    "_ws_subscribe",
    "_ws_view",
]
