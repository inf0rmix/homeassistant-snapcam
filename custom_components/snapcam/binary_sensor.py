
from __future__ import annotations
from typing import Any
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.entity import EntityCategory
from .const import DOMAIN, DATA_STORES, PULSE_SECONDS

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    store = hass.data.get(DATA_STORES, {}).get(entry.entry_id)
    if store is None:
        return
    async_add_entities([SnapCamTriggeredBinarySensor(hass, entry, store)])

class SnapCamTriggeredBinarySensor(BinarySensorEntity):
    _attr_has_entity_name = False
    _attr_name = "SnapCam Triggered"
    _attr_device_class = "motion"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, store) -> None:
        self.hass, self.entry, self.store = hass, entry, store
        self._is_on = False
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_triggered"

    @property
    def name(self) -> str: return "SnapCam Triggered"
    @property
    def device_info(self) -> dict[str, Any]:
        return {"identifiers": {(DOMAIN, self.entry.entry_id)}, "name": "SnapCam", "manufacturer": "Custom", "model": "Virtual Snapshot Camera"}
    @property
    def is_on(self) -> bool: return self._is_on
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        ts = getattr(self.store, "last_update_ts", None)
        return {"last_triggered": ts.isoformat() if ts else None}

    def pulse_triggered(self) -> None:
        if self.store.trigger_pulse_off:
            try: self.store.trigger_pulse_off()
            except Exception: pass
            self.store.trigger_pulse_off = None
        self._is_on = True; self.async_write_ha_state()
        def _off(_):
            self._is_on = False
            self.async_write_ha_state()
            self.store.trigger_pulse_off = None
        self.store.trigger_pulse_off = async_call_later(self.hass, PULSE_SECONDS, _off)
