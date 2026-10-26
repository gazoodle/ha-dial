"""Repair flow which restarts Home Assistant after an integration update."""

from __future__ import annotations

import voluptuous as vol
from homeassistant.components.repairs import (
    ConfirmRepairFlow,
    RepairsFlow,
    RepairsFlowResult,
)
from homeassistant.core import HomeAssistant

from .restart_notice import ISSUE_ID


class RestartRequiredRepairFlow(RepairsFlow):
    async def async_step_init(
        self, user_input: dict[str, str] | None = None
    ) -> RepairsFlowResult:
        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input: dict[str, str] | None = None
    ) -> RepairsFlowResult:
        if user_input is not None:
            await self.hass.services.async_call("homeassistant", "restart", blocking=False)
            return self.async_create_entry(data={})
        return self.async_show_form(
            step_id="confirm", data_schema=vol.Schema({}), last_step=True
        )


async def async_create_fix_flow(
    hass: HomeAssistant,
    issue_id: str,
    data: dict[str, str | int | float | None] | None,
) -> RepairsFlow:
    if issue_id == ISSUE_ID:
        return RestartRequiredRepairFlow()
    return ConfirmRepairFlow()
