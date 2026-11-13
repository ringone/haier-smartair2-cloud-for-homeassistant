"""Download local packet diagnostics without exporting connection details."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntry

from . import HaierConfigEntry
from .const import DOMAIN
from .packet_history import MAX_RECORDS, RETENTION_SECONDS, SAMPLE_INTERVAL


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: HaierConfigEntry
) -> dict[str, Any]:
    """Return recent local packets from this entry."""
    return _export(entry)


async def async_get_device_diagnostics(
    hass: HomeAssistant, entry: HaierConfigEntry, device: DeviceEntry
) -> dict[str, Any]:
    """Return recent packets for the selected device only."""
    mac = next((identifier for domain, identifier in device.identifiers if domain == DOMAIN), "")
    return _export(entry, mac)


def _export(entry: HaierConfigEntry, device: str | None = None) -> dict[str, Any]:
    history = entry.runtime_data.packet_history
    return {
        "schema_version": 1,
        "retention_seconds": RETENTION_SECONDS,
        "sample_interval_seconds": SAMPLE_INTERVAL,
        "max_records_per_entry": MAX_RECORDS,
        "local_packets": history.diagnostics(device),
    }
