
from __future__ import annotations
from typing import Any
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import EntityCategory
from .const import DOMAIN, DATA_STORES

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    store = hass.data.get(DATA_STORES, {}).get(entry.entry_id)
    if store is None:
        return
    async_add_entities([
        SnapCamLastSourceSensor(hass, entry, store),
        SnapCamLastTriggeredSensor(hass, entry, store),
    ])

class SnapCamLastSourceSensor(SensorEntity):
    _attr_has_entity_name = False
    _attr_name = "SnapCam Last Source"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, store) -> None:
        self.hass, self.entry, self.store = hass, entry, store
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_last_source"

    @property
    def name(self) -> str: return "SnapCam Last Source"
    @property
    def device_info(self) -> dict[str, Any]:
        return {"identifiers": {(DOMAIN, self.entry.entry_id)}, "name": "SnapCam", "manufacturer": "Custom", "model": "Virtual Snapshot Camera"}
    @property
    def native_value(self) -> str | None: return self.store.last_source_camera

class SnapCamLastTriggeredSensor(SensorEntity):
    _attr_has_entity_name = False
    _attr_name = "SnapCam Last Triggered"
    _attr_device_class = "timestamp"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, store) -> None:
        self.hass, self.entry, self.store = hass, entry, store
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_last_triggered"

    @property
    def name(self) -> str: return "SnapCam Last Triggered"
    @property
    def device_info(self) -> dict[str, Any]:
        return {"identifiers": {(DOMAIN, self.entry.entry_id)}, "name": "SnapCam", "manufacturer": "Custom", "model": "Virtual Snapshot Camera"}
    @property
    def native_value(self):
        return getattr(self.store, "last_update_ts", None)  # tz-aware datetime
