
from __future__ import annotations
from typing import Any, Callable, Optional, List
from dataclasses import dataclass
import random, base64, logging
from pathlib import Path
import voluptuous as vol
from homeassistant.components.camera import Camera, async_get_image
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_state_change, async_track_state_change_event
from homeassistant.helpers.entity_platform import AddEntitiesCallback, async_get_current_platform
from homeassistant.util import dt as dt_util
from homeassistant.helpers import config_validation as cv

from .const import *

_LOGGER = logging.getLogger(__name__)
ATTR_SOURCE_CAMERA = "source_camera"

_PLACEHOLDER_JPEG = base64.b64decode(
    b"/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////2wBDAf//////////////////////////////////////////////////////////////////////////////////////wAARCAAQABADASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAb/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAgP/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIRAxEAPwD3gA//2Q=="
)

@dataclass
class Pair:
    source_kind: str  # entity | file | url
    camera: Optional[str] = None   # entity_id when source_kind=entity
    file_path: Optional[str] = None
    url: Optional[str] = None
    trigger_type: str = TRIGGER_STATE
    state_entity: Optional[str] = None
    state_to: Optional[str] = None
    state_from: Optional[str] = None
    event_type: Optional[str] = None
    event_data: Optional[dict] = None

class SnapStore:
    def __init__(self) -> None:
        self.current: Optional[bytes] = None
        self.last: Optional[bytes] = None
        self.last_update_ts = None  # tz-aware datetime
        self.last_source_camera: Optional[str] = None
        self.trigger_pulse_off = None

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    data = dict(entry.data); data.update(entry.options)
    create_last = bool(data.get(CONF_CREATE_LAST, False))

    store = hass.data.setdefault(DATA_STORES, {}).get(entry.entry_id)
    if store is None:
        store = SnapStore()
        hass.data[DATA_STORES][entry.entry_id] = store

    main = SnapCamCamera(hass, entry, store, role="current")
    entities = [main]
    if create_last:
        entities.append(SnapCamCamera(hass, entry, store, role="last"))
    async_add_entities(entities)
    hass.data[DATA_ENTITIES][entry.entry_id] = entities

    platform = async_get_current_platform()
    platform.async_register_entity_service(
        "request_snapshot",
        cv.make_entity_service_schema({vol.Optional(ATTR_SOURCE_CAMERA): cv.entity_id}),
        "async_request_snapshot",
    )

class SnapCamCamera(Camera):
    _attr_has_entity_name = False
    _attr_name = None
    _attr_content_type = "image/jpeg"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, store: 'SnapStore', role: str="current") -> None:
        super().__init__()
        self.hass, self.entry, self.store, self.role = hass, entry, store, role
        data = dict(entry.data); data.update(entry.options)

        self._cam_name = data.get(CONF_CAM_NAME, "SnapCam")
        self._cam_description = data.get(CONF_CAM_DESCRIPTION, "")
        self._cooldown_min = float(data.get(CONF_DELAY_MIN, DEFAULT_DELAY_MIN))  # cooldown semantics
        self._pairs: List[Pair] = []
        for p in data.get(CONF_PAIRS, []) or []:
            kind = p.get(KEY_PAIR_SOURCE_KIND) or ("entity" if p.get(KEY_PAIR_CAMERA) else ("file" if p.get(KEY_PAIR_FILE) else ("url" if p.get(KEY_PAIR_URL) else "entity")))
            ttype = p.get(KEY_TRIGGER_TYPE, TRIGGER_STATE)
            pair = Pair(
                source_kind=kind,
                camera=p.get(KEY_PAIR_CAMERA),
                file_path=self._normalize_path(p.get(KEY_PAIR_FILE)) if p.get(KEY_PAIR_FILE) else None,
                url=p.get(KEY_PAIR_URL),
                trigger_type=ttype,
                state_entity=p.get(KEY_STATE_ENTITY),
                state_to=p.get(KEY_STATE_TO) or DEFAULT_TO_STATE,
                state_from=p.get(KEY_STATE_FROM),
                event_type=p.get(KEY_EVENT_TYPE),
                event_data=p.get(KEY_EVENT_DATA),
            )
            self._pairs.append(pair)

        self._unsubscribers: List[Callable[[], None]] = []
        suffix = "" if self.role == "current" else "_last"
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}{suffix}"
        self._attr_motion_detection_enabled = False
        self._attr_should_poll = False

    def _normalize_path(self, p: str) -> str:
        if not p:
            return p
        p = p.strip()
        if p.startswith("/local/"):
            rel = p[len("/local/"):]
            return str(Path(self.hass.config.path("www")) / rel)
        if not p.startswith("/"):
            return str(Path(self.hass.config.path(p)))
        return p

    @property
    def name(self) -> str:
        return self._cam_name if self.role == "current" else f"{self._cam_name}_last"

    @property
    def device_info(self) -> dict[str, Any]:
        return {"identifiers": {(DOMAIN, self.entry.entry_id)}, "name": self._cam_name, "manufacturer": "Custom", "model": "Virtual Snapshot Camera"}

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        ts = getattr(self.store, "last_update_ts", None)
        return {
            "description": self._cam_description, "cooldown_min": self._cooldown_min,
            "pairs": [self._pair_to_attr(p) for p in self._pairs],
            "last_update": ts.isoformat() if ts else None,
            "last_source_camera": self.store.last_source_camera, "role": self.role,
        }

    def _pair_to_attr(self, p: Pair) -> dict:
        d = {"source_kind": p.source_kind, "camera": p.camera, "file_path": p.file_path, "url": p.url, "trigger_type": p.trigger_type}
        if p.trigger_type == TRIGGER_STATE:
            d.update({"entity_id": p.state_entity, "to": p.state_to, "from": p.state_from})
        else:
            d.update({"event_type": p.event_type, "event_data": p.event_data})
        return d

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if self.role == "current":
            self._subscribe_triggers()
        self._attr_entity_picture = f"/api/camera_proxy/{self.entity_id}"
        self.async_write_ha_state()
        await self._initial_snapshot()

    async def async_will_remove_from_hass(self) -> None:
        await super().async_will_remove_from_hass()
        await self.async_remove_listeners()

    async def async_remove_listeners(self) -> None:
        for unsub in self._unsubscribers:
            try: unsub()
            except Exception: pass
        self._unsubscribers.clear()

    def _subscribe_triggers(self) -> None:
        for u in self._unsubscribers:
            try: u()
            except Exception: pass
        self._unsubscribers.clear()

        if not self._pairs:
            _LOGGER.debug("SnapCam[%s]: no pairs -> no subscriptions", self.entry.entry_id); return

        state_entities = [p.state_entity for p in self._pairs if p.trigger_type == TRIGGER_STATE and p.state_entity]
        if state_entities:
            async def _state_cb(entity, old, new):
                old_val = (old.state.lower() if old else None)
                new_val = (new.state.lower() if new else None)
                _LOGGER.debug("SnapCam[%s]: state_cb %s %s -> %s", self.entry.entry_id, entity, old_val, new_val)
                if new_val == old_val:
                    return
                for pair in [pp for pp in self._pairs if pp.trigger_type == TRIGGER_STATE and pp.state_entity == entity]:
                    ok_from = (pair.state_from is None) or (old_val == (pair.state_from or "").lower())
                    to_target = (pair.state_to or DEFAULT_TO_STATE).lower()
                    ok_to = (new_val == to_target)
                    if ok_from and ok_to:
                        _LOGGER.debug("SnapCam[%s]: MATCH %s from=%s to=%s -> immediate snapshot (cooldown)", self.entry.entry_id, entity, old_val, new_val)
                        self._trigger_snapshot_immediate(pair)
            unsub = async_track_state_change(self.hass, state_entities, _state_cb)
            self._unsubscribers.append(unsub)
            _LOGGER.debug("SnapCam[%s]: subscribed state %s", self.entry.entry_id, state_entities)

            def _event_cb(event):
                entity = event.data.get("entity_id")
                old = event.data.get("old_state")
                new = event.data.get("new_state")
                old_val = (getattr(old, "state", None) or "").lower() if old else None
                new_val = (getattr(new, "state", None) or "").lower() if new else None
                _LOGGER.debug("SnapCam[%s]: state_event %s %s -> %s", self.entry.entry_id, entity, old_val, new_val)
                if entity in state_entities and new_val != old_val:
                    for pair in [pp for pp in self._pairs if pp.trigger_type == TRIGGER_STATE and pp.state_entity == entity]:
                        ok_from = (pair.state_from is None) or (old_val == (pair.state_from or "").lower())
                        to_target = (pair.state_to or DEFAULT_TO_STATE).lower()
                        ok_to = (new_val == to_target)
                        if ok_from and ok_to:
                            _LOGGER.debug("SnapCam[%s]: MATCH(event) %s -> immediate snapshot (cooldown)", self.entry.entry_id, entity)
                            self._trigger_snapshot_immediate(pair)
            from homeassistant.helpers.event import async_track_state_change_event
            unsub2 = async_track_state_change_event(self.hass, state_entities, _event_cb)
            self._unsubscribers.append(unsub2)
            _LOGGER.debug("SnapCam[%s]: subscribed state-event %s", self.entry.entry_id, state_entities)

        for p in self._pairs:
            if p.trigger_type == TRIGGER_EVENT and p.event_type:
                def make_handler(pair: Pair):
                    def _h(event):
                        if pair.event_data:
                            for k, v in pair.event_data.items():
                                if event.data.get(k) != v: return
                        _LOGGER.debug("SnapCam[%s]: event '%s' matched -> immediate snapshot (cooldown)", self.entry.entry_id, pair.event_type)
                        self._trigger_snapshot_immediate(pair)
                    return _h
                unsub = self.hass.bus.async_listen(p.event_type, make_handler(p))
                self._unsubscribers.append(unsub)
                _LOGGER.debug("SnapCam[%s]: subscribed event %s filter=%s", self.entry.entry_id, p.event_type, p.event_data)

    async def _initial_snapshot(self) -> None:
        if not self._pairs: return
        first = random.choice(self._pairs)
        await self._do_snapshot(first)
        has_last = any(getattr(e, "role", "") == "last" for e in self.hass.data.get(DATA_ENTITIES, {}).get(self.entry.entry_id, []))
        if has_last:
            second = random.choice(self._pairs); await self._do_snapshot(second)

    def _select_label(self, pair: Pair) -> str:
        return pair.camera or pair.file_path or pair.url or "unknown"

    def _cooldown_ok(self) -> bool:
        if self.store.last_update_ts is None:
            return True
        delta = (dt_util.now() - self.store.last_update_ts).total_seconds() / 60.0
        return delta >= float(self._cooldown_min)

    def _trigger_snapshot_immediate(self, pair: Pair) -> None:
        if self._cooldown_ok():
            self.hass.loop.call_soon_threadsafe(lambda: self.hass.async_create_task(self._do_snapshot(pair)))
        else:
            remain = (float(self._cooldown_min) * 60.0) - (dt_util.now() - (self.store.last_update_ts or dt_util.now())).total_seconds()
            _LOGGER.debug("SnapCam[%s]: cooldown active (%.1fs remaining) -> skip", self.entry.entry_id, max(0.0, remain))

    async def _load_bytes(self, pair: Pair) -> Optional[bytes]:
        if pair.source_kind == "entity" and pair.camera:
            img = await async_get_image(self.hass, pair.camera)
            return img.content if img else None
        if pair.source_kind == "file" and pair.file_path:
            path = Path(pair.file_path)
            def _io():
                if path.exists() and path.is_file():
                    return path.read_bytes()
                return None
            return await self.hass.async_add_executor_job(_io)
        if pair.source_kind == "url" and pair.url:
            try:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.get(pair.url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                        if resp.status == 200:
                            return await resp.read()
            except Exception as err:
                _LOGGER.warning("SnapCam[%s]: URL fetch failed: %s", self.entry.entry_id, err)
            return None
        return None

    async def _do_snapshot(self, pair: Pair) -> None:
        try:
            content = await self._load_bytes(pair)
            prev = self.store.current
            if content is not None:
                self.store.last = prev
                self.store.current = content
                self.store.last_update_ts = dt_util.now()  # tz-aware datetime
                self.store.last_source_camera = self._select_label(pair)
                self._attr_entity_picture = f"/api/camera_proxy/{self.entity_id}"
                self.async_write_ha_state()
                _LOGGER.debug("SnapCam[%s]: snapshot OK from %s (%d bytes)", self.entry.entry_id, self.store.last_source_camera, len(content))
            else:
                _LOGGER.warning("SnapCam[%s]: snapshot returned empty from %s", self.entry.entry_id, self._select_label(pair))
        except Exception as err:
            _LOGGER.warning("SnapCam[%s]: snapshot failed: %s", self.entry.entry_id, err)

    async def async_camera_image(self, width: int | None = None, height: int | None = None) -> bytes | None:
        return self.store.current if self.role == "current" else (self.store.last or self.store.current) or _PLACEHOLDER_JPEG

    async def async_update_from_entry(self) -> None:
        pass

    async def async_request_snapshot(self, source_camera: str | None = None) -> None:
        pair = None
        if source_camera:
            for p in self._pairs:
                if p.source_kind == "entity" and p.camera == source_camera:
                    pair = p; break
        if pair is None and self._pairs:
            pair = random.choice(self._pairs)
        if pair:
            await self._do_snapshot(pair)
