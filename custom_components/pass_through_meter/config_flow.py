from typing import Mapping, Optional

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.const import CONF_DEVICE, CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry, selector
from homeassistant.helpers.entity_registry import RegistryEntryHider

from . import CONF_HIDE_MEMBERS, CONF_INPUTS, CONF_OUTPUTS, DOMAIN


class PTMConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: Optional[Mapping] = None):
        if user_input:
            _async_hide_members(
                self.hass,
                user_input[CONF_INPUTS] + user_input[CONF_OUTPUTS],
                RegistryEntryHider.INTEGRATION,
            )
            return self.async_create_entry(
                title=user_input.get(CONF_NAME, ""),
                data={},
                options={
                    CONF_DEVICE: user_input.get(CONF_DEVICE, None),
                    CONF_HIDE_MEMBERS: user_input[CONF_HIDE_MEMBERS],
                    CONF_INPUTS: user_input[CONF_INPUTS],
                    CONF_OUTPUTS: user_input[CONF_OUTPUTS],
                },
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_INPUTS): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="sensor", device_class="energy", multiple=True),
                ),
                vol.Required(CONF_OUTPUTS): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="sensor", device_class="energy", multiple=True),
                ),
                vol.Optional(CONF_DEVICE): selector.DeviceSelector(),
                vol.Optional(CONF_NAME): selector.TextSelector(),
                vol.Required(CONF_HIDE_MEMBERS, default=False): selector.BooleanSelector(),
            })
        )

    @staticmethod
    @callback
    def async_get_options_flow(entry: ConfigEntry):
        return PTMOptionsFlow(entry)


class PTMOptionsFlow(OptionsFlow):
    def __init__(self, entry: ConfigEntry):
        self.config_entry = entry

    async def async_step_init(self, user_input: Optional[Mapping] = None):
        if user_input:
            _async_hide_members(
                self.hass,
                user_input[CONF_INPUTS] + user_input[CONF_OUTPUTS],
                RegistryEntryHider.INTEGRATION if user_input[CONF_HIDE_MEMBERS] else None,
            )
            return self.async_create_entry(
                title="",
                data={
                    CONF_DEVICE: user_input.get(CONF_DEVICE, None),
                    CONF_HIDE_MEMBERS: user_input[CONF_HIDE_MEMBERS],
                    CONF_INPUTS: user_input[CONF_INPUTS],
                    CONF_OUTPUTS: user_input[CONF_OUTPUTS],
                },
            )

        data = self.config_entry.options
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(CONF_INPUTS, default=data[CONF_INPUTS]): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="sensor", device_class="energy", multiple=True),
                ),
                vol.Required(CONF_OUTPUTS, default=data[CONF_OUTPUTS]): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="sensor", device_class="energy", multiple=True),
                ),
                vol.Optional(CONF_DEVICE, default=data.get(CONF_DEVICE, None)): selector.DeviceSelector(),
                vol.Required(CONF_HIDE_MEMBERS, default=data[CONF_HIDE_MEMBERS]): selector.BooleanSelector(),
            })
        )


def _async_hide_members(hass: HomeAssistant, members: list[str], hidden_by: Optional[RegistryEntryHider]):
    registry = entity_registry.async_get(hass)
    for member in members:
        if not (entity_id := entity_registry.async_resolve_entity_id(registry, member)):
            continue
        if entity_id not in registry.entities:
            continue
        registry.async_update_entity(entity_id, hidden_by=hidden_by)
