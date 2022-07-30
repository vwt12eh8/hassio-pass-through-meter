from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry
from homeassistant.helpers.entity_registry import RegistryEntryHider

CONF_HIDE_MEMBERS = "hide_members"
CONF_INPUTS = "inputs"
CONF_OUTPUTS = "outputs"
DOMAIN = "pass_through_meter"

_PLATFORMS = {
    Platform.SENSOR,
}


async def _on_updated(hass: HomeAssistant, entry: ConfigEntry):
    await hass.config_entries.async_reload(entry.entry_id)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    entry.async_on_unload(entry.add_update_listener(_on_updated))
    hass.config_entries.async_setup_platforms(entry, _PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    return await hass.config_entries.async_unload_platforms(entry, _PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry):
    registry = entity_registry.async_get(hass)

    if not entry.options[CONF_HIDE_MEMBERS]:
        return

    for member in entry.options[CONF_INPUTS] + entry.options[CONF_OUTPUTS]:
        if not (entity_id := entity_registry.async_resolve_entity_id(registry, member)):
            continue
        if (entity_entry := registry.async_get(entity_id)) is None:
            continue
        if entity_entry.hidden_by != RegistryEntryHider.INTEGRATION:
            continue
        registry.async_update_entity(entity_id, hidden_by=None)
