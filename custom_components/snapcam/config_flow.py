
from __future__ import annotations
import json
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector as sel
from homeassistant.core import callback
from .const import *

def _norm_pairs(data, options):
    pairs = (options.get(CONF_PAIRS) if options and isinstance(options.get(CONF_PAIRS), list) else None)
    if pairs is None:
        pairs = data.get(CONF_PAIRS, []) if data else []
    return [p for p in pairs if isinstance(p, dict)]

class SnapCamConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 20

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            self._base = user_input; self._pairs: list[dict] = []
            return await self.async_step_add_pair_source()

        schema = vol.Schema({
            vol.Required(CONF_CAM_NAME): sel.selector({"text": {}}),
            vol.Optional(CONF_CAM_DESCRIPTION, default=""): sel.selector({"text": {}}),
            vol.Required(CONF_DELAY_MIN, default=DEFAULT_DELAY_MIN): sel.selector({"number": {"min": 0, "max": MAX_DELAY_MIN, "step": 1, "mode": "slider"}}),
            vol.Optional(CONF_CREATE_LAST, default=False): sel.selector({"boolean": {}}),
        })
        return self.async_show_form(step_id="user", data_schema=schema)

    async def async_step_add_pair_source(self, user_input=None):
        if user_input is not None:
            self._pair_source_kind = user_input[KEY_PAIR_SOURCE_KIND]
            if self._pair_source_kind == "entity":
                return await self.async_step_add_pair_type()
            elif self._pair_source_kind == "file":
                return await self.async_step_add_pair_file()
            else:
                return await self.async_step_add_pair_url()

        schema = vol.Schema({
            vol.Required(KEY_PAIR_SOURCE_KIND, default="entity"): sel.selector({"select": {"options": ["entity", "file", "url"]}})
        })
        return self.async_show_form(step_id="add_pair_source", data_schema=schema)

    async def async_step_add_pair_file(self, user_input=None):
        if user_input is not None:
            self._pair_file = user_input[KEY_PAIR_FILE]
            return await self.async_step_add_pair_type()

        schema = vol.Schema({
            vol.Required(KEY_PAIR_FILE): sel.selector({"text": {"placeholder": "/config/www/snapshots/vehicle_detection_latest.jpg (oder /local/snapshots/...)"}}),
        })
        return self.async_show_form(step_id="add_pair_file", data_schema=schema)

    async def async_step_add_pair_url(self, user_input=None):
        if user_input is not None:
            self._pair_url = user_input[KEY_PAIR_URL]
            return await self.async_step_add_pair_type()

        schema = vol.Schema({
            vol.Required(KEY_PAIR_URL): sel.selector({"text": {"placeholder": "https://example.local/local/snapshots/vehicle_detection_latest.jpg"}}),
        })
        return self.async_show_form(step_id="add_pair_url", data_schema=schema)

    async def async_step_add_pair_type(self, user_input=None):
        if user_input is not None:
            self._pair_type = user_input[KEY_TRIGGER_TYPE]
            return await (self.async_step_add_pair_state() if self._pair_type == TRIGGER_STATE else self.async_step_add_pair_event())

        schema = vol.Schema({
            vol.Required(KEY_TRIGGER_TYPE, default=TRIGGER_STATE): sel.selector({"select": {"options": [TRIGGER_STATE, TRIGGER_EVENT]}})
        })
        return self.async_show_form(step_id="add_pair_type", data_schema=schema)

    async def async_step_add_pair_state(self, user_input=None):
        if user_input is not None:
            pair = {
                KEY_PAIR_SOURCE_KIND: getattr(self, "_pair_source_kind", "entity"),
                KEY_TRIGGER_TYPE: TRIGGER_STATE,
                KEY_STATE_ENTITY: user_input[KEY_STATE_ENTITY],
                KEY_STATE_TO: user_input.get(KEY_STATE_TO) or DEFAULT_TO_STATE,
                KEY_STATE_FROM: user_input.get(KEY_STATE_FROM),
            }
            if self._pair_source_kind == "entity":
                pair[KEY_PAIR_CAMERA] = user_input[KEY_PAIR_CAMERA]
            elif self._pair_source_kind == "file":
                pair[KEY_PAIR_FILE] = getattr(self, "_pair_file", "")
            else:
                pair[KEY_PAIR_URL] = getattr(self, "_pair_url", "")

            self._pairs.append(pair)
            if user_input.get("add_another"): return await self.async_step_add_pair_source()
            data = dict(self._base); data[CONF_PAIRS] = self._pairs
            return self.async_create_entry(title=str(self._base.get(CONF_CAM_NAME, "SnapCam")), data=data)

        base_fields = {}
        if getattr(self, "_pair_source_kind", "entity") == "entity":
            base_fields[vol.Required(KEY_PAIR_CAMERA)] = sel.selector({"entity": {"domain": "camera"}})

        schema = vol.Schema({
            **base_fields,
            vol.Required(KEY_STATE_ENTITY): sel.selector({"entity": {"filter": [{"domain": "binary_sensor"}, {"domain": "sensor"}, {"domain": "person"}, {"domain": "device_tracker"}]}}),
            vol.Optional(KEY_STATE_TO, default=DEFAULT_TO_STATE): sel.selector({"text": {}}),
            vol.Optional(KEY_STATE_FROM): sel.selector({"text": {}}),
            vol.Optional("add_another", default=False): sel.selector({"boolean": {}}),
        })
        return self.async_show_form(step_id="add_pair_state", data_schema=schema)

    async def async_step_add_pair_event(self, user_input=None):
        if user_input is not None:
            edata = None
            if user_input.get(KEY_EVENT_DATA):
                try: edata = json.loads(user_input[KEY_EVENT_DATA])
                except Exception: edata = None

            pair = {
                KEY_PAIR_SOURCE_KIND: getattr(self, "_pair_source_kind", "entity"),
                KEY_TRIGGER_TYPE: TRIGGER_EVENT,
                KEY_EVENT_TYPE: user_input[KEY_EVENT_TYPE],
                KEY_EVENT_DATA: edata,
            }
            if self._pair_source_kind == "entity":
                pair[KEY_PAIR_CAMERA] = user_input[KEY_PAIR_CAMERA]
            elif self._pair_source_kind == "file":
                pair[KEY_PAIR_FILE] = getattr(self, "_pair_file", "")
            else:
                pair[KEY_PAIR_URL] = getattr(self, "_pair_url", "")

            self._pairs.append(pair)
            if user_input.get("add_another"): return await self.async_step_add_pair_source()
            data = dict(self._base); data[CONF_PAIRS] = self._pairs
            return self.async_create_entry(title=str(self._base.get(CONF_CAM_NAME, "SnapCam")), data=data)

        base_fields = {}
        if getattr(self, "_pair_source_kind", "entity") == "entity":
            base_fields[vol.Required(KEY_PAIR_CAMERA)] = sel.selector({"entity": {"domain": "camera"}})

        schema = vol.Schema({
            **base_fields,
            vol.Required(KEY_EVENT_TYPE): sel.selector({"text": {}}),
            vol.Optional(KEY_EVENT_DATA): sel.selector({"text": {}}),
            vol.Optional("add_another", default=False): sel.selector({"boolean": {}}),
        })
        return self.async_show_form(step_id="add_pair_event", data_schema=schema)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return SnapCamOptionsFlow(config_entry)

class SnapCamOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, entry):
        self.entry = entry
        self._pairs = _norm_pairs(entry.data, entry.options)
        self._editing_index = None
        self._temp_pair = {}

    def _merged(self):
        data = dict(self.entry.data); data.update(self.entry.options or {})
        data[CONF_PAIRS] = self._pairs
        return data

    async def async_step_init(self, user_input=None):
        return await self.async_step_menu()

    async def async_step_menu(self, user_input=None):
        options = ["Edit general options", "Add new pair", "Edit existing pair", "Remove pair", "Finish"]
        if user_input is not None:
            choice = user_input["menu"]
            if choice == "Edit general options":
                return await self.async_step_edit_general()
            if choice == "Add new pair":
                return await self.async_step_pair_source_new()
            if choice == "Edit existing pair":
                return await self.async_step_pick_pair_to_edit()
            if choice == "Remove pair":
                return await self.async_step_pick_pair_to_remove()
            return self.async_create_entry(title="", data=self._merged())

        schema = vol.Schema({
            vol.Required("menu"): sel.selector({"select": {"options": options}})
        })
        return self.async_show_form(step_id="menu", data_schema=schema, description_placeholders={})

    async def async_step_edit_general(self, user_input=None):
        data = self._merged()
        if user_input is not None:
            if CONF_DELAY_MIN in user_input: data[CONF_DELAY_MIN] = user_input[CONF_DELAY_MIN]
            if CONF_CAM_DESCRIPTION in user_input: data[CONF_CAM_DESCRIPTION] = user_input[CONF_CAM_DESCRIPTION]
            if CONF_CREATE_LAST in user_input: data[CONF_CREATE_LAST] = user_input[CONF_CREATE_LAST]
            return self.async_create_entry(title="", data=data)

        schema = vol.Schema({
            vol.Required(CONF_DELAY_MIN, default=data.get(CONF_DELAY_MIN, DEFAULT_DELAY_MIN)): sel.selector({"number": {"min": 0, "max": MAX_DELAY_MIN, "step": 1}}),
            vol.Optional(CONF_CAM_DESCRIPTION, default=data.get(CONF_CAM_DESCRIPTION, "")): sel.selector({"text": {}}),
            vol.Optional(CONF_CREATE_LAST, default=data.get(CONF_CREATE_LAST, False)): sel.selector({"boolean": {}}),
        })
        return self.async_show_form(step_id="edit_general", data_schema=schema)

    async def async_step_pair_source_new(self, user_input=None):
        if user_input is not None:
            self._temp_pair = {KEY_PAIR_SOURCE_KIND: user_input[KEY_PAIR_SOURCE_KIND]}
            return await self.async_step_pair_trigger_type_new()

        schema = vol.Schema({
            vol.Required(KEY_PAIR_SOURCE_KIND, default="entity"): sel.selector({"select": {"options": ["entity", "file", "url"]}})
        })
        return self.async_show_form(step_id="pair_source_new", data_schema=schema)

    async def async_step_pair_trigger_type_new(self, user_input=None):
        if user_input is not None:
            self._temp_pair[KEY_TRIGGER_TYPE] = user_input[KEY_TRIGGER_TYPE]
            if user_input[KEY_TRIGGER_TYPE] == TRIGGER_STATE:
                return await self.async_step_pair_state_new()
            else:
                return await self.async_step_pair_event_new()

        schema = vol.Schema({
            vol.Required(KEY_TRIGGER_TYPE, default=TRIGGER_STATE): sel.selector({"select": {"options": [TRIGGER_STATE, TRIGGER_EVENT]}})
        })
        return self.async_show_form(step_id="pair_trigger_type_new", data_schema=schema)

    async def async_step_pair_state_new(self, user_input=None):
        if user_input is not None:
            p = dict(self._temp_pair)
            p[KEY_STATE_ENTITY] = user_input[KEY_STATE_ENTITY]
            p[KEY_STATE_TO] = user_input.get(KEY_STATE_TO) or DEFAULT_TO_STATE
            p[KEY_STATE_FROM] = user_input.get(KEY_STATE_FROM)
            kind = p[KEY_PAIR_SOURCE_KIND]
            if kind == "entity": p[KEY_PAIR_CAMERA] = user_input[KEY_PAIR_CAMERA]
            if kind == "file": p[KEY_PAIR_FILE] = user_input[KEY_PAIR_FILE]
            if kind == "url": p[KEY_PAIR_URL] = user_input[KEY_PAIR_URL]
            self._pairs.append(p)
            return await self.async_step_menu()

        base_fields = {}
        kind = self._temp_pair.get(KEY_PAIR_SOURCE_KIND, "entity")
        if kind == "entity":
            base_fields[vol.Required(KEY_PAIR_CAMERA)] = sel.selector({"entity": {"domain": "camera"}})
        elif kind == "file":
            base_fields[vol.Required(KEY_PAIR_FILE)] = sel.selector({"text": {"placeholder": "/local/snapshots/..."}})
        else:
            base_fields[vol.Required(KEY_PAIR_URL)] = sel.selector({"text": {"placeholder": "https://..."}})

        schema = vol.Schema({
            **base_fields,
            vol.Required(KEY_STATE_ENTITY): sel.selector({"entity": {"filter": [{"domain": "binary_sensor"}, {"domain": "sensor"}, {"domain": "person"}, {"domain": "device_tracker"}]}}),
            vol.Optional(KEY_STATE_TO, default=DEFAULT_TO_STATE): sel.selector({"text": {}}),
            vol.Optional(KEY_STATE_FROM): sel.selector({"text": {}}),
        })
        return self.async_show_form(step_id="pair_state_new", data_schema=schema)

    async def async_step_pair_event_new(self, user_input=None):
        if user_input is not None:
            p = dict(self._temp_pair)
            p[KEY_EVENT_TYPE] = user_input[KEY_EVENT_TYPE]
            edata = None
            if user_input.get(KEY_EVENT_DATA):
                try: edata = json.loads(user_input[KEY_EVENT_DATA])
                except Exception: edata = None
            p[KEY_EVENT_DATA] = edata
            kind = p[KEY_PAIR_SOURCE_KIND]
            if kind == "entity": p[KEY_PAIR_CAMERA] = user_input[KEY_PAIR_CAMERA]
            if kind == "file": p[KEY_PAIR_FILE] = user_input[KEY_PAIR_FILE]
            if kind == "url": p[KEY_PAIR_URL] = user_input[KEY_PAIR_URL]
            self._pairs.append(p)
            return await self.async_step_menu()

        base_fields = {}
        kind = self._temp_pair.get(KEY_PAIR_SOURCE_KIND, "entity")
        if kind == "entity":
            base_fields[vol.Required(KEY_PAIR_CAMERA)] = sel.selector({"entity": {"domain": "camera"}})
        elif kind == "file":
            base_fields[vol.Required(KEY_PAIR_FILE)] = sel.selector({"text": {"placeholder": "/local/snapshots/..."}})
        else:
            base_fields[vol.Required(KEY_PAIR_URL)] = sel.selector({"text": {"placeholder": "https://..."}})

        schema = vol.Schema({
            **base_fields,
            vol.Required(KEY_EVENT_TYPE): sel.selector({"text": {}}),
            vol.Optional(KEY_EVENT_DATA): sel.selector({"text": {}}),
        })
        return self.async_show_form(step_id="pair_event_new", data_schema=schema)

    async def async_step_pick_pair_to_edit(self, user_input=None):
        if not self._pairs:
            return await self.async_step_menu()
        options = [f"#{i}: {p.get(KEY_PAIR_SOURCE_KIND)} / {p.get(KEY_TRIGGER_TYPE)}" for i, p in enumerate(self._pairs)]
        if user_input is not None:
            idx = user_input["pair_index"]
            self._editing_index = int(idx.split(':')[0][1:]) if isinstance(idx, str) else idx
            p = self._pairs[self._editing_index]
            self._temp_pair = dict(p)
            if p.get(KEY_TRIGGER_TYPE) == TRIGGER_STATE:
                return await self.async_step_pair_state_edit()
            else:
                return await self.async_step_pair_event_edit()

        schema = vol.Schema({
            vol.Required("pair_index"): sel.selector({"select": {"options": options}})
        })
        return self.async_show_form(step_id="pick_pair_to_edit", data_schema=schema)

    async def async_step_pair_state_edit(self, user_input=None):
        p = self._temp_pair
        if user_input is not None:
            p[KEY_STATE_ENTITY] = user_input[KEY_STATE_ENTITY]
            p[KEY_STATE_TO] = user_input.get(KEY_STATE_TO) or DEFAULT_TO_STATE
            p[KEY_STATE_FROM] = user_input.get(KEY_STATE_FROM)
            kind = p.get(KEY_PAIR_SOURCE_KIND, "entity")
            if kind == "entity": p[KEY_PAIR_CAMERA] = user_input[KEY_PAIR_CAMERA]
            if kind == "file": p[KEY_PAIR_FILE] = user_input[KEY_PAIR_FILE]
            if kind == "url": p[KEY_PAIR_URL] = user_input[KEY_PAIR_URL]
            self._pairs[self._editing_index] = p
            return await self.async_step_menu()

        kind = p.get(KEY_PAIR_SOURCE_KIND, "entity")
        base_fields = {}
        if kind == "entity":
            base_fields[vol.Required(KEY_PAIR_CAMERA, default=p.get(KEY_PAIR_CAMERA))] = sel.selector({"entity": {"domain": "camera"}})
        elif kind == "file":
            base_fields[vol.Required(KEY_PAIR_FILE, default=p.get(KEY_PAIR_FILE,""))] = sel.selector({"text": {}})
        else:
            base_fields[vol.Required(KEY_PAIR_URL, default=p.get(KEY_PAIR_URL,""))] = sel.selector({"text": {}})

        schema = vol.Schema({
            **base_fields,
            vol.Required(KEY_STATE_ENTITY, default=p.get(KEY_STATE_ENTITY,"")): sel.selector({"entity": {"filter": [{"domain": "binary_sensor"}, {"domain": "sensor"}, {"domain": "person"}, {"domain": "device_tracker"}]}}),
            vol.Optional(KEY_STATE_TO, default=p.get(KEY_STATE_TO, DEFAULT_TO_STATE)): sel.selector({"text": {}}),
            vol.Optional(KEY_STATE_FROM, default=p.get(KEY_STATE_FROM, "")): sel.selector({"text": {}}),
        })
        return self.async_show_form(step_id="pair_state_edit", data_schema=schema)

    async def async_step_pair_event_edit(self, user_input=None):
        p = self._temp_pair
        if user_input is not None:
            p[KEY_EVENT_TYPE] = user_input[KEY_EVENT_TYPE]
            edata = None
            if user_input.get(KEY_EVENT_DATA):
                try: edata = json.loads(user_input[KEY_EVENT_DATA])
                except Exception: edata = None
            p[KEY_EVENT_DATA] = edata
            kind = p.get(KEY_PAIR_SOURCE_KIND, "entity")
            if kind == "entity": p[KEY_PAIR_CAMERA] = user_input[KEY_PAIR_CAMERA]
            if kind == "file": p[KEY_PAIR_FILE] = user_input[KEY_PAIR_FILE]
            if kind == "url": p[KEY_PAIR_URL] = user_input[KEY_PAIR_URL]
            self._pairs[self._editing_index] = p
            return await self.async_step_menu()

        kind = p.get(KEY_PAIR_SOURCE_KIND, "entity")
        base_fields = {}
        if kind == "entity":
            base_fields[vol.Required(KEY_PAIR_CAMERA, default=p.get(KEY_PAIR_CAMERA))] = sel.selector({"entity": {"domain": "camera"}})
        elif kind == "file":
            base_fields[vol.Required(KEY_PAIR_FILE, default=p.get(KEY_PAIR_FILE,""))] = sel.selector({"text": {}})
        else:
            base_fields[vol.Required(KEY_PAIR_URL, default=p.get(KEY_PAIR_URL,""))] = sel.selector({"text": {}})

        schema = vol.Schema({
            **base_fields,
            vol.Required(KEY_EVENT_TYPE, default=p.get(KEY_EVENT_TYPE,"")): sel.selector({"text": {}}),
            vol.Optional(KEY_EVENT_DATA, default=json.dumps(p.get(KEY_EVENT_DATA)) if p.get(KEY_EVENT_DATA) else ""): sel.selector({"text": {}}),
        })
        return self.async_show_form(step_id="pair_event_edit", data_schema=schema)

    async def async_step_pick_pair_to_remove(self, user_input=None):
        if not self._pairs:
            return await self.async_step_menu()
        options = [f"#{i}: {p.get(KEY_PAIR_SOURCE_KIND)} / {p.get(KEY_TRIGGER_TYPE)}" for i, p in enumerate(self._pairs)]
        if user_input is not None:
            idx = user_input["pair_index"]
            i = int(idx.split(':')[0][1:]) if isinstance(idx, str) else idx
            if 0 <= i < len(self._pairs):
                self._pairs.pop(i)
            return await self.async_step_menu()

        schema = vol.Schema({
            vol.Required("pair_index"): sel.selector({"select": {"options": options}})
        })
        return self.async_show_form(step_id="pick_pair_to_remove", data_schema=schema)
