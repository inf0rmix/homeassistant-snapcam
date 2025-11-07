
from __future__ import annotations
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
from .const import DOMAIN, PLATFORMS, DATA_ENTITIES, DATA_STORES

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    _LOGGER.debug("SnapCam: setup entry %s", entry.entry_id)
    hass.data.setdefault(DATA_ENTITIES, {})
    hass.data.setdefault(DATA_STORES, {})
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    return True

async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    _LOGGER.debug("SnapCam: reload entry %s", entry.entry_id)
    await hass.config_entries.async_reload(entry.entry_id)

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    _LOGGER.debug("SnapCam: unload entry %s", entry.entry_id)
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        for ent in hass.data.get(DATA_ENTITIES, {}).pop(entry.entry_id, []) or []:
            try:
                await ent.async_remove_listeners()
            except Exception:
                pass
        hass.data.get(DATA_STORES, {}).pop(entry.entry_id, None)
    return unload_ok
