"""Haier SmartAir2, using only configured direct LAN connections."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr

from .const import CONF_LOCAL_IPS, DOMAIN, PLATFORMS
from .coordinator import HaierCoordinator
from .local import HaierLocalClient
from .local_map import format_local_map, parse_local_map
from .local_setup import codec_for_status
from .packet_history import PacketHistory, history_store

_LOGGER = logging.getLogger(__name__)
FIRST_STATUS_TIMEOUT = 15


@dataclass
class HaierData:
    """Runtime data for a local-only config entry."""

    packet_history: PacketHistory
    local_clients: list[HaierLocalClient] = field(default_factory=list)
    coordinators: list[HaierCoordinator] = field(default_factory=list)


type HaierConfigEntry = ConfigEntry[HaierData]


async def async_migrate_entry(hass: HomeAssistant, entry: HaierConfigEntry) -> bool:
    """Remove cloud credentials in place; retain entry and MAC-based entity IDs."""
    if entry.version > 2:
        return False
    if entry.version == 1:
        # Match the original runtime's whole-field options precedence. Unioning
        # maps would resurrect devices intentionally removed through Options.
        local_ips = {**entry.data, **entry.options}.get(CONF_LOCAL_IPS, "")
        if not isinstance(local_ips, str):
            local_ips = ""
        try:
            local_ips = format_local_map(parse_local_map(local_ips))
        except ValueError:
            # Keep invalid/empty effective input for repair through Options.
            pass
        hass.config_entries.async_update_entry(
            entry, data={CONF_LOCAL_IPS: local_ips}, options={}, version=2, minor_version=1
        )
    return True


async def _async_update_listener(hass: HomeAssistant, entry: HaierConfigEntry) -> None:
    """Reload after the user edits the local mapping."""
    await hass.config_entries.async_reload(entry.entry_id)


def _device_name(hass: HomeAssistant, devid: str, entry_id: str) -> str:
    registry = dr.async_get(hass)
    if (lookup := getattr(registry, "async_get_device_by_identifier", None)) is not None:
        device = lookup((DOMAIN, devid), entry_id)
    else:
        device = registry.async_get_device(identifiers={(DOMAIN, devid)})
    if device is not None:
        return device.name or device.name_by_user or f"Haier {devid}"
    return f"Haier {devid}"


async def _async_stop(data: HaierData) -> None:
    """Try every client even when a previous cleanup fails."""
    results = await asyncio.gather(
        *(client.async_stop() for client in data.local_clients), return_exceptions=True
    )
    for result in results:
        if isinstance(result, BaseException):
            _LOGGER.warning("Haier local client cleanup failed: %s", result)
    await data.packet_history.async_flush()


async def async_setup_entry(hass: HomeAssistant, entry: HaierConfigEntry) -> bool:
    """Set up exactly the configured devices; never contact a cloud service."""
    conf = {**entry.data, **entry.options}
    try:
        local_map = parse_local_map(conf.get(CONF_LOCAL_IPS))
    except ValueError as err:
        raise ConfigEntryNotReady(
            "Configure the local MAC:IPv4 map in this integration's Options: " + str(err)
        ) from err

    history = PacketHistory(history_store(hass, entry.entry_id))
    data = HaierData(packet_history=history)
    forwarding = False
    try:
        await history.async_load()
        for devid, ip in local_map.items():
            local = HaierLocalClient(hass, ip, devid, history)
            data.local_clients.append(local)
            async with asyncio.timeout(FIRST_STATUS_TIMEOUT):
                await local.async_start()
                await local.async_poll(devid)
                while (frame := local.latest_frame(devid)) is None:
                    await asyncio.sleep(0.1)
                codec = codec_for_status(frame)
                coord = HaierCoordinator(
                    hass, local, codec, devid, _device_name(hass, devid, entry.entry_id),
                    via_cloud=False, config_entry=entry
                )
                data.coordinators.append(coord)
                await coord.async_config_entry_first_refresh()
        entry.runtime_data = data
        forwarding = True
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    except (Exception, asyncio.CancelledError) as err:
        if forwarding:
            try:
                await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
            except Exception:
                _LOGGER.exception("Unable to unload partially initialized Haier platforms")
        await _async_stop(data)
        entry.runtime_data = None
        if isinstance(err, asyncio.CancelledError):
            raise
        detail = "Timed out waiting for the first local status" if isinstance(err, TimeoutError) else str(err)
        raise ConfigEntryNotReady(
            f"Haier local setup failed; check the configured MAC:IPv4 map and LAN access: {detail}"
        ) from err
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: HaierConfigEntry) -> bool:
    """Unload platforms, close LAN clients and persist local packet history."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await _async_stop(entry.runtime_data)
    return unload_ok


async def async_remove_entry(hass: HomeAssistant, entry: HaierConfigEntry) -> None:
    """Delete local packet history only when the user removes the entry."""
    await history_store(hass, entry.entry_id).async_remove()
