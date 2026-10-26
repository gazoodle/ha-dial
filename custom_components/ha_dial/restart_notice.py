"""Raise a Repair when the installer has put newer code on disk."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .deployment import pending_restart

HERE = Path(__file__).parent
DOMAIN = HERE.name
ISSUE_ID = "restart_required"
NOTIFICATION_ID = f"{DOMAIN}_restart"


async def async_check_restart(
    hass: Any, loaded_version: str | None, loaded_revision: str
) -> None:
    from homeassistant.components import persistent_notification
    from homeassistant.helpers import issue_registry as ir

    update = await hass.async_add_executor_job(pending_restart, loaded_revision, HERE)
    if update is None:
        ir.async_delete_issue(hass, DOMAIN, ISSUE_ID)
        persistent_notification.async_dismiss(hass, NOTIFICATION_ID)
        return
    to_version = update.get("to_version") or "unchanged version"
    if ir.async_get(hass).async_get_issue(DOMAIN, ISSUE_ID) is None:
        persistent_notification.async_create(
            hass,
            f"HA Dial code was updated from {loaded_version or 'unknown'} to {to_version}. "
            "Restart Home Assistant to load it.",
            title="HA Dial: restart Home Assistant",
            notification_id=NOTIFICATION_ID,
        )
    ir.async_create_issue(
        hass,
        DOMAIN,
        ISSUE_ID,
        is_fixable=True,
        severity=ir.IssueSeverity.WARNING,
        translation_key=ISSUE_ID,
        translation_placeholders={
            "from_version": loaded_version or "unknown",
            "to_version": str(to_version),
        },
    )
