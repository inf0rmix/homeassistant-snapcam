
DOMAIN = "snapcam"
PLATFORMS = ["camera", "binary_sensor", "sensor", "button"]

# Main config
CONF_CAM_NAME = "cam_name"
CONF_CAM_DESCRIPTION = "cam_description"
CONF_DELAY_MIN = "delay_min"              # cooldown minutes
CONF_CREATE_LAST = "create_last_camera"

# Trigger pairs list
CONF_PAIRS = "pairs"
KEY_PAIR_SOURCE_KIND = "pair_source_kind"  # entity | file | url
KEY_PAIR_CAMERA = "pair_camera"            # when kind=entity
KEY_PAIR_FILE = "pair_file"                # when kind=file
KEY_PAIR_URL = "pair_url"                  # when kind=url

# Trigger schema (automation-like)
KEY_TRIGGER_TYPE = "trigger_type"        # "state" | "event"
TRIGGER_STATE = "state"
TRIGGER_EVENT = "event"

# state trigger
KEY_STATE_ENTITY = "entity_id"
KEY_STATE_TO = "to"
KEY_STATE_FROM = "from"

# event trigger
KEY_EVENT_TYPE = "event_type"
KEY_EVENT_DATA = "event_data"            # JSON (dict) optional

DEFAULT_TO_STATE = "on"  # default for state trigger
DEFAULT_DELAY_MIN = 15
MAX_DELAY_MIN = 30

DATA_ENTITIES = f"{DOMAIN}_entities"  # per entry_id: list of camera entities
DATA_STORES = f"{DOMAIN}_stores"      # per entry_id: shared store among entities
PULSE_SECONDS = 5.0
