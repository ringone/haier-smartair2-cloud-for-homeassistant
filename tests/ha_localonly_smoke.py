"""Framework-level offline smoke check; run separately from stub unit tests.

Requires Home Assistant >= 2026.11. Uses a loopback AC simulator, never hardware.
Run: python tests/ha_localonly_smoke.py
"""
from __future__ import annotations

import asyncio
import importlib
import importlib.abc
import json
from pathlib import Path
import socket
import sys
import tempfile
from types import MappingProxyType
from unittest.mock import AsyncMock, patch

from homeassistant import loader
from homeassistant.config_entries import ConfigEntries, ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.const import __version__ as HA_VERSION
from homeassistant.helpers import device_registry as dr, frame

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DOMAIN = "haier_smartair2"
MAC = "001122334455"
NORMAL = bytes.fromhex("ffff2a400000000000026d01060a850002010000000029004e00000300000000000000000000000000000000ec4268")
EXTENDED = bytes.fromhex("ffff38400000000000027d01060a850002010000000029004e0000030000000000000000000000000000000000007c7e0000462801ff5502250058462efc")


class NoCloudImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.startswith("paho") or fullname == f"custom_components.{DOMAIN}.cloud":
            raise AssertionError(f"Cloud import is forbidden: {fullname}")
        return None


def envelope(payload):
    header = bytearray(80)
    header[2:4] = b"\x27\x15"
    header[40:52] = MAC.encode()
    header[79] = len(payload)
    return bytes(header) + payload


async def main():
    probe = NoCloudImports()
    sys.meta_path.insert(0, probe)
    integration = importlib.import_module(f"custom_components.{DOMAIN}")
    flow_module = importlib.import_module(f"custom_components.{DOMAIN}.config_flow")
    local = importlib.import_module(f"custom_components.{DOMAIN}.local")
    peers = []
    polls = []
    network_attempts = []

    async def air_conditioner(reader, writer):
        peers.append(writer)
        try:
            while True:
                header = await reader.readexactly(80)
                payload = await reader.readexactly(header[79])
                polls.append(payload.hex())
                response = EXTENDED if payload[10:12] == b"\x4d\xfe" else NORMAL
                writer.write(envelope(response))
                await writer.drain()
        except (asyncio.IncompleteReadError, ConnectionError):
            pass
        finally:
            writer.close()
            await writer.wait_closed()

    original_connect = socket.socket.connect
    original_getaddrinfo = socket.getaddrinfo

    def loopback_connect(sock, address):
        if isinstance(address, tuple):
            network_attempts.append(address)
            assert address[0] in ("127.0.0.1", "::1"), f"Non-local connection: {address}"
        return original_connect(sock, address)

    def loopback_dns(host, *args, **kwargs):
        assert host in ("127.0.0.1", "::1", None), f"Unexpected DNS: {host}"
        return original_getaddrinfo(host, *args, **kwargs)

    server = await asyncio.start_server(air_conditioner, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    scratch = ROOT.parent
    with tempfile.TemporaryDirectory(prefix="ha-local-smoke-", dir=scratch) as config_dir:
        hass = HomeAssistant(config_dir)
        frame.async_setup(hass)
        loader.async_setup(hass)
        hass.config_entries = ConfigEntries(hass, {})
        hass.data[dr.DATA_REGISTRY] = dr.DeviceRegistry(hass)
        await dr.async_get(hass).async_load()
        entry = ConfigEntry(
            domain=DOMAIN, version=1, minor_version=1, source="user",
            data={"username": "old@example.invalid", "password": "not-a-real-password", "region": "eu", "client_id": "legacy", "local_ips": f"{MAC}:192.168.1.9"},
            options={"local_ips": f"{MAC}:127.0.0.1"},
            title="Haier legacy", unique_id="legacy@example.invalid",
            discovery_keys=MappingProxyType({}), subentries_data=None,
        )
        hass.config_entries._entries[entry.entry_id] = entry
        registry = dr.async_get(hass)
        device = registry.async_get_or_create(config_entry_id=entry.entry_id, identifiers={(DOMAIN, MAC)}, name="Existing bedroom")
        registry.async_update_device(device.id, name_by_user="Quarto")
        original_entry_id = entry.entry_id
        forwarded = AsyncMock()
        with patch.object(socket.socket, "connect", loopback_connect), patch.object(socket, "getaddrinfo", loopback_dns), patch.object(local, "LOCAL_PORT", port), patch.object(hass.config_entries, "async_forward_entry_setups", forwarded), patch.object(hass.config_entries, "async_unload_platforms", AsyncMock(return_value=True)):
            assert await integration.async_migrate_entry(hass, entry)
            assert entry.version == 2 and entry.entry_id == original_entry_id
            assert "127.0.0.1" in str(entry.data) + str(entry.options)
            assert not any(key in entry.data or key in entry.options for key in ("username", "password", "region", "client_id"))
            flow = flow_module.HaierConfigFlow()
            flow.hass = hass
            form = await flow.async_step_user()
            fields = {str(key.schema) for key in form["data_schema"].schema}
            assert fields == {"local_ips"}, fields
            entry._async_set_state(hass, ConfigEntryState.SETUP_IN_PROGRESS, None)
            assert await integration.async_setup_entry(hass, entry)
            assert len(entry.runtime_data.coordinators) == 1
            coord = entry.runtime_data.coordinators[0]
            assert coord.devid == MAC and coord.via_cloud is False
            assert coord.dev_name in ("Quarto", "Existing bedroom"), coord.dev_name
            assert coord.data.target_temp == 22.0 and coord.data.current_temp == 20.5
            entities = []
            for platform in ("climate", "sensor", "binary_sensor", "switch", "select"):
                module = importlib.import_module(f"custom_components.{DOMAIN}.{platform}")
                await module.async_setup_entry(hass, entry, lambda group: entities.extend(group))
            climate = next(entity for entity in entities if type(entity).__name__ == "HaierClimate")
            assert climate.unique_id == f"{DOMAIN}_{MAC}"
            assert any("compressor" in str(entity.unique_id) for entity in entities)
            await coord.async_apply(health=True)
            assert await integration.async_unload_entry(hass, entry)
        await hass.async_stop(force=True)
        result = {"home_assistant": HA_VERSION, "migration_preserves_entry_id": True, "credentials_removed": True, "config_fields": sorted(fields), "local_setup": True, "device_name": coord.dev_name, "entity_count": len(entities), "climate_unique_id": climate.unique_id, "poll_and_command_frames": len(polls), "network_connections": [list(address) for address in network_attempts], "cloud_imports_or_connections": 0, "unload": True}
    server.close()
    await server.wait_closed()
    for writer in peers:
        writer.close()
    sys.meta_path.remove(probe)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
