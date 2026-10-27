"""Config flow for HA Dial."""

from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_ENTITY_ID
from homeassistant.core import callback
from homeassistant.helpers.selector import EntitySelector, EntitySelectorConfig

from .const import DOMAIN


class HaDialConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        if user_input is not None:
            return self.async_create_entry(title="HA Dial", data=user_input)
        return self.async_show_form(step_id="user", data_schema=_schema())

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return HaDialOptionsFlow()


class HaDialOptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        current = self.config_entry.options.get(
            CONF_ENTITY_ID, self.config_entry.data.get(CONF_ENTITY_ID)
        )
        return self.async_show_form(step_id="init", data_schema=_schema(current))


def _schema(current=None):
    entity = (
        vol.Optional(CONF_ENTITY_ID, default=current)
        if current
        else vol.Optional(CONF_ENTITY_ID)
    )
    return vol.Schema({entity: EntitySelector(EntitySelectorConfig(domain="light"))})
