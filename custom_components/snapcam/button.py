
from __future__ import annotations
from typing import Any
from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import EntityCategory
from .const import DOMAIN, DATA_ENTITIES

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    current_cam = None
    for ent in hass.data.get(DATA_ENTITIES, {}).get(entry.entry_id, []):
        if getattr(ent, "role", None) == "current":
            current_cam = ent
            break
    if current_cam is None:
        return
    async_add_entities([SnapCamSnapshotButton(hass, entry, current_cam)])

class SnapCamSnapshotButton(ButtonEntity):
    _attr_has_entity_name = False
    _attr_name = "SnapCam Take Snapshot"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, current_cam) -> None:
        self.hass, self.entry, self.current_cam = hass, entry, current_cam
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_button_snapshot"

    @property
    def name(self) -> str: return "SnapCam Take Snapshot"

    @property
    def device_info(self) -> dict[str, Any]:
        return {"identifiers": {(DOMAIN, self.entry.entry_id)}, "name": getattr(self.current_cam, "_cam_name", "SnapCam"), "manufacturer": "Custom", "model": "Virtual Snapshot Camera"}

    async def async_press(self) -> None:
        await self.current_cam.async_request_snapshot(None)
