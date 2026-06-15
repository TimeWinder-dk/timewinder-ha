"""The TimeWinder Operations Hub integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import TimeWinderClient
from .const import CONF_BASE_URL, CONF_TOKEN
from .coordinator import TimeWinderCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]

# Config entry whose runtime_data holds the coordinator.
TimeWinderConfigEntry = ConfigEntry  # subscripted alias kept simple for older cores


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up TimeWinder Operations Hub from a config entry."""
    session = async_get_clientsession(hass)
    client = TimeWinderClient(session, entry.data[CONF_BASE_URL], entry.data[CONF_TOKEN])
    coordinator = TimeWinderCoordinator(hass, entry, client)

    # Raises ConfigEntryAuthFailed (-> reauth) or ConfigEntryNotReady as appropriate.
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload_on_update))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_reload_on_update(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
