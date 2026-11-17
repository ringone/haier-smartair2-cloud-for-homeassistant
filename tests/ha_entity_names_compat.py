"""Offline REAL Home Assistant entity-name and registry regressions.

Run in its own HA environment, never in the stub unittest process::

    python -B tests/ha_entity_names_compat.py -v

Uses unchanged product async_setup_entry functions, real HA translation loading,
entity platforms, state machine and entity/device registry storage. Both V2 and
V3 local coordinator fixtures are used; only their data/listeners/command boundary
are fake. No entity naming output or translation dictionary is patched.

Legacy records below are synthetic pre-upgrade registry fixtures (including the
old Portuguese battery label), not an old integration execution. Registry/config
entry Stores are actually saved and loaded into a NEW HomeAssistant instance.
This is an in-process HA-instance restart, not a process or complete HA bootstrap.
Config entries are inserted directly before exercising real platform setup; no
transport, physical AC, frontend rendering or running recorder is tested. Climate
has name=None intentionally and inherits the device name. Option translations are
resolved by HA's backend loader; HA states retain internal option keys.
Names are checked using server/registration language pt, not a frontend user's
language. New registrations may get different default entity IDs after a label
change; only existing registry identity is required to remain unchanged. A fresh
HA instance reloads translations; live file hot-reload is not claimed here.

All temporary HA configuration/registry writes are under ROOT.parent. DNS and
socket connection/datagram operations are denied, including worker threads.
The ha_ filename intentionally excludes this from test*.py stub discovery.
"""
from __future__ import annotations

import asyncio
from contextlib import ExitStack, contextmanager
import importlib
import json
import logging
from pathlib import Path
import socket
import sys
import tempfile
from types import MappingProxyType, SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from homeassistant import loader
from homeassistant.config_entries import ConfigEntries, ConfigEntry, ConfigEntryState
from homeassistant.const import __version__ as HA_VERSION
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry, entity_registry, frame, translation

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True
DOMAIN = "haier_smartair2"
PREFIX = f"component.{DOMAIN}.entity."
V3_MAC = "001122334455"
V2_MAC = "aabbccddeeff"
PLATFORMS = ("climate", "sensor", "binary_sensor", "switch", "select")
# Independent identity contract: do not derive these from product entity tables.
SUFFIXES = {
    "climate": ("",),
    "sensor": (
        "current_temp", "outdoor_temp", "humidity", "indoor_coil_temp",
        "outdoor_coil_temp", "outdoor_in_temp", "outdoor_out_temp", "defrost_temp",
        "compressor_hz", "compressor_current", "power_w", "expansion_valve",
        "error_code", "operation_source",
    ),
    "binary_sensor": (
        "filter_change", "compressor_on", "indoor_fan_on", "defrost_on",
        "outdoor_fan", "four_way_valve", "indoor_electric_heat_on", "alarm_bits",
    ),
    "switch": ("health", "display", "self_clean", "lock_remote", "electric_heat"),
    "select": ("vertical_swing",),
}
SELECT_KEYS = ("auto", "health_up", "max_up", "health_down", "up", "center", "down", "max_down")
PRESET_KEYS = ("none", "boost", "sleep")
FAN_KEYS = {
    V3_MAC: ("auto", "quiet", "low", "medium", "high"),
    V2_MAC: ("auto", "quiet", "low", "medium", "high", "turbo"),
}
USER_ENTITY_NAME = "Nome escolhido pelo utilizador"
USER_DEVICE_NAME = "AC da sala — nome pessoal"


def expected_identities():
    """Enumerate the stable IDs emitted for local V3 and local V2 products."""
    expected = {
        (domain, f"{DOMAIN}_{V3_MAC}" + (f"_{suffix}" if suffix else ""))
        for domain, suffixes in SUFFIXES.items() for suffix in suffixes
    }
    expected.update({("climate", f"{DOMAIN}_{V2_MAC}"), ("sensor", f"{DOMAIN}_{V2_MAC}_current_temp")})
    return expected


@contextmanager
def offline_guard():
    """Fail closed on DNS, TCP/Unix connections and UDP destinations."""
    attempts = []

    def forbidden(*args, **kwargs):
        attempts.append((args, kwargs))
        raise AssertionError("network forbidden: entity-name harness is offline")

    with ExitStack() as stack:
        for name in ("getaddrinfo", "gethostbyname", "gethostbyname_ex", "gethostbyaddr", "create_connection"):
            stack.enter_context(patch.object(socket, name, forbidden))
        for name in ("connect", "connect_ex", "sendto", "sendmsg"):
            stack.enter_context(patch.object(socket.socket, name, forbidden))
        yield attempts


class OfflineGuardTests(unittest.TestCase):
    def test_dns_and_socket_destinations_are_denied(self):
        with offline_guard():
            for operation, args in (
                (socket.getaddrinfo, ("fixture.invalid", 443)),
                (socket.gethostbyname, ("fixture.invalid",)),
                (socket.gethostbyname_ex, ("fixture.invalid",)),
                (socket.gethostbyaddr, ("192.0.2.1",)),
                (socket.create_connection, (("192.0.2.1", 443),)),
            ):
                with self.subTest(operation=operation.__name__):
                    with self.assertRaisesRegex(AssertionError, "network forbidden"):
                        operation(*args)
            with socket.socket() as client:
                for method in (client.connect, client.connect_ex):
                    with self.assertRaisesRegex(AssertionError, "network forbidden"):
                        method(("192.0.2.1", 443))
            with socket.socket(type=socket.SOCK_DGRAM) as client:
                with self.assertRaisesRegex(AssertionError, "network forbidden"):
                    client.sendto(b"fixture", ("192.0.2.1", 443))
                with self.assertRaisesRegex(AssertionError, "network forbidden"):
                    client.sendmsg([b"fixture"], [], 0, ("192.0.2.1", 443))


class EntityNamesRegistryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="ha-entity-names-", dir=ROOT.parent)
        self.addCleanup(self.directory.cleanup)
        self.guard = offline_guard()
        self.network_attempts = self.guard.__enter__()
        self.addCleanup(self.guard.__exit__, None, None, None)
        self.addCleanup(lambda: self.assertEqual(self.network_attempts, [], "Even swallowed network attempts must fail"))
        # Read the CURRENT worktree, not a frozen pre-review Portuguese mapping.
        self.pt = json.loads((ROOT / "custom_components" / DOMAIN / "translations" / "pt.json").read_text())
        self.hass = None
        await self._new_hass()

    async def asyncTearDown(self):
        if self.hass is not None:
            await self.hass.async_stop(force=True)

    async def _new_hass(self, *, entry_id=None):
        self.hass = HomeAssistant(self.directory.name)
        self.hass.config.language = "pt"
        frame.async_setup(self.hass)
        loader.async_setup(self.hass)
        integration = await loader.async_get_integration(self.hass, DOMAIN)
        self.assertEqual(integration.file_path.resolve(), (ROOT / "custom_components" / DOMAIN).resolve())
        self.hass.config_entries = ConfigEntries(self.hass, {})
        await self.hass.config_entries.async_initialize()
        self.hass.data[device_registry.DATA_REGISTRY] = device_registry.DeviceRegistry(self.hass)
        self.hass.data[entity_registry.DATA_REGISTRY] = entity_registry.EntityRegistry(self.hass)
        await device_registry.async_get(self.hass).async_load()
        await entity_registry.async_get(self.hass).async_load()
        if entry_id is None:
            self.entry = ConfigEntry(
                domain=DOMAIN, version=2, minor_version=1, source="user", data={}, options={},
                title="Fixture AC", unique_id=None, discovery_keys=MappingProxyType({}),
                subentries_data=None,
            )
            self.hass.config_entries._entries[self.entry.entry_id] = self.entry
        else:
            self.entry = self.hass.config_entries.async_get_entry(entry_id)
            self.assertIsNotNone(self.entry, "ConfigEntry must reload from its real Store")
        self.entry._async_set_state(self.hass, ConfigEntryState.SETUP_IN_PROGRESS, None)
        codec = importlib.import_module(f"custom_components.{DOMAIN}.codec")
        const = importlib.import_module(f"custom_components.{DOMAIN}.const")
        state = codec.HaierState(
            current_temp=20.5, target_temp=22.0, power=True, mode=const.MODE_COOL,
            fan=const.FAN_AUTO, quiet=False, turbo=False, sleep=False, swing_v=False,
            swing_pos=0x06, operation_source="wifi",
        )
        self.coordinators = [
            SimpleNamespace(
                data=state, codec=product_codec, devid=mac, dev_name=f"Fixture {label}",
                via_cloud=False, last_update_success=True,
                async_add_listener=lambda listener, context=None: lambda: None,
                async_apply=AsyncMock(),
            )
            for product_codec, mac, label in ((codec.CodecV3(), V3_MAC, "V3"), (codec.CodecV2(), V2_MAC, "V2"))
        ]
        self.entry.runtime_data = SimpleNamespace(coordinators=self.coordinators)
        self.platforms = {}

    async def _setup_product_platforms(self):
        for domain in PLATFORMS:
            component_module = importlib.import_module(f"homeassistant.components.{domain}")
            product = importlib.import_module(f"custom_components.{DOMAIN}.{domain}")
            async with asyncio.timeout(15):
                self.assertTrue(await component_module.async_setup(self.hass, {}))
                component = self.hass.data[domain]
                platform = component._async_init_entity_platform(DOMAIN, DOMAIN, product)
                self.assertTrue(await platform.async_setup_entry(self.entry))
            self.platforms[domain] = platform
        await self.hass.async_block_till_done()

    def _records(self):
        registry = entity_registry.async_get(self.hass)
        return {
            (record.domain, record.unique_id): record
            for record in registry.entities.values()
            if record.platform == DOMAIN
        }

    def _assert_ids_and_names(self):
        records = self._records()
        self.assertEqual(set(records), expected_identities())
        self.assertEqual(len({record.id for record in records.values()}), len(records))
        for (domain, unique_id), record in records.items():
            self.assertEqual(record.config_entry_id, self.entry.entry_id, unique_id)
            self.assertIsNotNone(record.device_id, unique_id)
            if domain == "climate":
                # The product explicitly has name=None; HA must not invent an AC label.
                self.assertIsNone(record.original_name, unique_id)
            else:
                expected = self.pt["entity"][domain][record.translation_key]["name"]
                self.assertEqual(record.original_name, expected, unique_id)
            entity = self.platforms[domain].entities.get(record.entity_id)
            if record.disabled:
                self.assertIsNone(entity, unique_id)
                self.assertIsNone(self.hass.states.get(record.entity_id), unique_id)
                continue
            self.assertIsNotNone(entity, unique_id)
            self.assertEqual(entity.unique_id, unique_id)
            self.assertEqual(entity.registry_entry.id, record.id, unique_id)
            self.assertEqual(entity.name, record.original_name, unique_id)
            state = self.hass.states.get(record.entity_id)
            self.assertIsNotNone(state, unique_id)
            device = device_registry.async_get(self.hass).async_get(record.device_id)
            device_name = device.name_by_user or device.name
            if record.name is not None:
                # has_entity_name=True: HA prefixes even a user entity label.
                friendly_name = f"{device_name} {record.name}"
            elif domain == "climate":
                friendly_name = device_name
            else:
                friendly_name = f"{device_name} {record.original_name}"
            self.assertEqual(state.attributes["friendly_name"], friendly_name, unique_id)
        return records

    async def _assert_option_keys_and_translations(self):
        resolved = await translation.async_get_translations(self.hass, "pt", "entity", {DOMAIN})
        # Verify EVERY leaf of the current Portuguese entity mapping via HA's loader.
        def leaves(value, path=()):
            if isinstance(value, dict):
                for key, child in value.items():
                    yield from leaves(child, (*path, key))
            else:
                yield ".".join(path), value

        for key, value in leaves(self.pt["entity"]):
            self.assertEqual(resolved[PREFIX + key], value, key)
        source = next(e for e in self.platforms["sensor"].entities.values()
                      if e.unique_id.endswith("_operation_source"))
        self.assertEqual(source.options, ["other", "remote", "panel", "wifi"])
        self.assertEqual(self.hass.states.get(source.entity_id).state, "wifi")
        swing = next(iter(self.platforms["select"].entities.values()))
        self.assertEqual(tuple(swing.options), SELECT_KEYS)
        self.assertEqual(tuple(self.hass.states.get(swing.entity_id).attributes["options"]), SELECT_KEYS)
        self.assertEqual(swing.current_option, "center")
        self.assertEqual(self.hass.states.get(swing.entity_id).state, "center")
        self.assertEqual(set(self.pt["entity"]["select"]["vertical_swing"]["state"]), set(SELECT_KEYS))
        for key in SELECT_KEYS:
            self.assertEqual(swing.platform_data.platform_translations[PREFIX + f"select.vertical_swing.state.{key}"],
                             self.pt["entity"]["select"]["vertical_swing"]["state"][key])
        climate = next(e for e in self.platforms["climate"].entities.values() if V3_MAC in e.unique_id)
        self.assertEqual(tuple(climate.preset_modes), PRESET_KEYS)
        self.assertEqual(tuple(climate.fan_modes), FAN_KEYS[V3_MAC])
        attributes = self.hass.states.get(climate.entity_id).attributes
        self.assertEqual(tuple(attributes["preset_modes"]), PRESET_KEYS)
        self.assertEqual(tuple(attributes["fan_modes"]), FAN_KEYS[V3_MAC])
        self.assertEqual(attributes["preset_mode"], "none")
        self.assertEqual(attributes["fan_mode"], "auto")
        for attribute, keys in (("preset_mode", PRESET_KEYS), ("fan_mode", ("quiet", "turbo"))):
            states = self.pt["entity"]["climate"]["ac"]["state_attributes"][attribute]["state"]
            self.assertEqual(set(states), set(keys))
            for key in keys:
                path = PREFIX + f"climate.ac.state_attributes.{attribute}.state.{key}"
                self.assertEqual(climate.platform_data.platform_translations[path], states[key])
        v2 = next(e for e in self.platforms["climate"].entities.values() if V2_MAC in e.unique_id)
        self.assertEqual(tuple(v2.fan_modes), FAN_KEYS[V2_MAC])
        self.assertEqual(tuple(self.hass.states.get(v2.entity_id).attributes["fan_modes"]), FAN_KEYS[V2_MAC])
        self.assertNotIn("preset_modes", self.hass.states.get(v2.entity_id).attributes)
        # Actual HA service validation/dispatch receives keys, never translated labels.
        for key, nibble in zip(SELECT_KEYS, (None, 0x01, 0x02, 0x03, 0x04, 0x06, 0x08, 0x0A), strict=True):
            swing.coordinator.async_apply.reset_mock()
            await self.hass.services.async_call("select", "select_option", {
                "entity_id": swing.entity_id, "option": key,
            }, blocking=True)
            swing.coordinator.async_apply.assert_awaited_once_with(
                **({"swing_v": True} if nibble is None else {"swing_pos": nibble})
            )
        for key, command in (
            ("none", {"turbo": False, "sleep": False}),
            ("boost", {"turbo": True, "sleep": False, "quiet": False, "power": True}),
            ("sleep", {"sleep": True, "turbo": False, "power": True}),
        ):
            climate.coordinator.async_apply.reset_mock()
            await self.hass.services.async_call("climate", "set_preset_mode", {
                "entity_id": climate.entity_id, "preset_mode": key,
            }, blocking=True)
            climate.coordinator.async_apply.assert_awaited_once_with(**command)
        const = importlib.import_module(f"custom_components.{DOMAIN}.const")
        for entity in (climate, v2):
            for key in FAN_KEYS[entity.coordinator.devid]:
                entity.coordinator.async_apply.reset_mock()
                await self.hass.services.async_call("climate", "set_fan_mode", {
                    "entity_id": entity.entity_id, "fan_mode": key,
                }, blocking=True)
                command = {"quiet": False, "turbo": False, "power": True}
                if key in ("quiet", "turbo"):
                    command[key] = True
                else:
                    command["fan"] = {"auto": const.FAN_AUTO, "low": const.FAN_LOW,
                                      "medium": const.FAN_MID, "high": const.FAN_HIGH}[key]
                entity.coordinator.async_apply.assert_awaited_once_with(**command)

    async def _seed_and_restart(self, *, customized):
        registry = entity_registry.async_get(self.hass)
        devices = device_registry.async_get(self.hass)
        device_ids = {}
        for coordinator in self.coordinators:
            device = devices.async_get_or_create(
                config_entry_id=self.entry.entry_id, identifiers={(DOMAIN, coordinator.devid)},
                name=coordinator.dev_name, manufacturer="Haier", model="SmartAir2 (local)",
            )
            if customized:
                device = devices.async_update_device(device.id, name_by_user=USER_DEVICE_NAME)
            device_ids[coordinator.devid] = device.id
        snapshots = {}
        for domain, unique_id in sorted(expected_identities()):
            mac = V3_MAC if V3_MAC in unique_id else V2_MAC
            legacy_name = ("Temperatura da bateria interior" if unique_id.endswith("_indoor_coil_temp")
                           else f"Designação anterior {unique_id}")
            # Only registry input is seeded. Entity.name and loaded translations stay real.
            record = registry.async_get_or_create(
                domain, DOMAIN, unique_id, config_entry=self.entry, device_id=device_ids[mac],
                has_entity_name=True, original_name=legacy_name, object_id_base=legacy_name,
                suggested_object_id=None, disabled_by=None,
            )
            if customized:
                record = registry.async_update_entity(record.entity_id, name=USER_ENTITY_NAME)
            snapshots[(domain, unique_id)] = (record.id, record.entity_id, record.unique_id, record.device_id)
        entry_id = self.entry.entry_id
        # Flush real HA Stores rather than replacing their load/save functions.
        for owner in (self.hass.config_entries, devices, registry):
            await owner._store.async_save(owner._data_to_save())
        for key in ("core.config_entries", "core.device_registry", "core.entity_registry"):
            self.assertTrue((Path(self.directory.name) / ".storage" / key).is_file())
        await self.hass.async_stop(force=True)
        self.hass = None
        await self._new_hass(entry_id=entry_id)
        self.assertEqual(
            {key: (record.id, record.entity_id, record.unique_id, record.device_id)
             for key, record in self._records().items()}, snapshots,
        )
        self.assertTrue(all(record.original_name for record in self._records().values()))
        await self._setup_product_platforms()
        records = self._assert_ids_and_names()
        self.assertEqual(
            {key: (record.id, record.entity_id, record.unique_id, record.device_id)
             for key, record in records.items()}, snapshots,
        )
        self.assertEqual(len(records), len(snapshots), "No duplicate/replacement registrations")
        for record in records.values():
            self.assertEqual(record.name, USER_ENTITY_NAME if customized else None)
            device = device_registry.async_get(self.hass).async_get(record.device_id)
            self.assertEqual(device.name_by_user, USER_DEVICE_NAME if customized else None)
        return len(records)

    async def test_all_product_ids_current_portuguese_names_and_option_keys(self):
        await self._setup_product_platforms()
        records = self._assert_ids_and_names()
        await self._assert_option_keys_and_translations()
        print(f"HA {HA_VERSION}: fresh registration: {len(records)} identities; all pt entity leaves resolved; internal select/preset/fan keys unchanged", flush=True)

    async def test_legacy_default_names_update_without_changing_persisted_ids(self):
        count = await self._seed_and_restart(customized=False)
        print(f"HA {HA_VERSION}: legacy defaults after real Store reload: {count} identities preserved; original_name updated to current pt.json (climate=None); legacy entity_id retained", flush=True)

    async def test_user_entity_and_device_names_survive_registry_reload_and_registration(self):
        count = await self._seed_and_restart(customized=True)
        print(f"HA {HA_VERSION}: user overrides after real Store reload: {count} identities/entity names preserved; both device name_by_user values preserved", flush=True)


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    unittest.main()
