"""Constants for the Haier SmartAir2 integration."""

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

CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_REGION = "region"
CONF_LOCAL_IPS = "local_ips"
CONF_CLIENT_ID = "client_id"

LOGIN_HOST = "uhome.haieriot.net"
LOGIN_PORT = 7263
APP_KEY = "c403cbfc780dd8a0ab68784bb6d3023b"
APP_ID = "MB-HKQHWBB-0001"
APP_VERSION = "3.2.1"
REST_CLIENT_ID = "4BC6E2ADBF06AD33FA18AC1190F3DED9"


def generate_client_id() -> str:
    """Random 32-hex gateway client id, one per HA installation."""
    import secrets

    return secrets.token_hex(16)


REGIONS = {
    "eu": "gw-gea-euro.haieriot.net",
    "us": "gw-gea-us.haieriot.net",
    "sg": "gw-gea-sg.haieriot.net",
}
DEFAULT_REGION = "eu"
MASTER_GW_PORT = 56815
LOCAL_PORT = 56800

AUTH_SALT = b"haier_sdk"

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
TOKEN_REFRESH_SECONDS = 30 * 60
