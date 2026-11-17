"""Constants for the local-only Haier SmartAir2 integration."""
from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "haier_smartair2"
PLATFORMS = [
    Platform.CLIMATE,
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SWITCH,
    Platform.SELECT,
]

CONF_LOCAL_IPS = "local_ips"
LOCAL_PORT = 56800

MODE_AUTO = 0
MODE_COOL = 1
MODE_HEAT = 2
MODE_FAN = 3
MODE_DRY = 4

FAN_HIGH = 0
FAN_MID = 1
FAN_LOW = 2
FAN_AUTO = 3

MIN_TEMP = 16
MAX_TEMP = 30
TEMP_STEP = 1.0

SCAN_INTERVAL_SECONDS = 30
