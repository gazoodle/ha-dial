"""What the websocket commands and the Dial's own events share."""

from __future__ import annotations

import re
from functools import wraps

import voluptuous as vol

from ..const import DOMAIN

INPUTS = {
    "ready",
    "rotate_left",
    "rotate_right",
    "set_value",
    "press",
    "touch",
    "back",
    "home",
}
DEVICE_RE = re.compile(r"^[a-z0-9_]{1,64}$")
DEVICE_SCHEMA = vol.All(str, vol.Match(DEVICE_RE))


def _require_server(handler):
    @wraps(handler)
    async def checked(hass, connection, msg):
        if not hass.data.get(DOMAIN, {}).get("active"):
            connection.send_error(
                msg["id"],
                "not_loaded",
                "Add HA Dial Server in Settings / Devices & services first",
            )
            return
        await handler(hass, connection, msg)

    return checked
