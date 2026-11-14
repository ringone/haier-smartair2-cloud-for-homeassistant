"""Real-framework climate compatibility tests; run outside stub discovery.

Requires Home Assistant >= 2026.11; never contacts a physical device.
Run: python tests/ha_climate_compat.py -v
"""
from __future__ import annotations

import asyncio
import importlib
import logging
from pathlib import Path
import socket
import sys
import tempfile
from types import MappingProxyType, SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from homeassistant import loader
from homeassistant.components import climate as ha_climate
from homeassistant.components.climate.const import DATA_COMPONENT
from homeassistant.config_entries import ConfigEntries, ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import device_registry, entity_registry, frame
from homeassistant.util.unit_system import METRIC_SYSTEM, US_CUSTOMARY_SYSTEM

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
MODULE = "custom_components.haier_smartair2.climate"


class Climate202611Tests(unittest.TestCase):
    def test_00_import_uses_native_temperature_api_without_warnings(self):
        """Do not rely on Home Assistant's temporary legacy-property adapter."""
        with self.assertNoLogs(MODULE, level="WARNING"):
            if MODULE in sys.modules:
                importlib.reload(sys.modules[MODULE])
            else:
                importlib.import_module(MODULE)


class ClimateRuntimeTests(unittest.IsolatedAsyncioTestCase):
    """Real entity state machine and service bus, with a fake device coordinator.

    Only the coordinator/device command boundary is a fixture. Entity registration,
    state conversion, service dispatch and temperature validation are real HA.
    """

    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="climate-202611-", dir=ROOT.parent)
        self.addCleanup(self.directory.cleanup)
        self.hass = HomeAssistant(self.directory.name)
        frame.async_setup(self.hass)
        loader.async_setup(self.hass)
        self.hass.config_entries = ConfigEntries(self.hass, {})
        await self.hass.config_entries.async_initialize()
        self.hass.data[device_registry.DATA_REGISTRY] = device_registry.DeviceRegistry(self.hass)
        self.hass.data[entity_registry.DATA_REGISTRY] = entity_registry.EntityRegistry(self.hass)
        await device_registry.async_get(self.hass).async_load()
        await entity_registry.async_get(self.hass).async_load()
        self.hass.config.units = METRIC_SYSTEM
        self.addCleanup(patch.stopall)
        patch.object(socket.socket, "connect", side_effect=AssertionError("No network in climate tests")).start()
        patch.object(socket, "getaddrinfo", side_effect=AssertionError("No DNS in climate tests")).start()
        product = importlib.import_module(MODULE)
        codec = importlib.import_module("custom_components.haier_smartair2.codec")
        constants = importlib.import_module("custom_components.haier_smartair2.const")
        self.coordinator = SimpleNamespace(
            data=codec.HaierState(current_temp=20.5, target_temp=22.0, power=True, mode=constants.MODE_COOL),
            codec=codec.CodecV3(), devid="001122334455", dev_name="Fixture AC",
            via_cloud=False, last_update_success=True,
            async_add_listener=lambda listener, context=None: lambda: None,
            async_apply=AsyncMock(),
        )
        self.entity = product.HaierClimate(self.coordinator)
        self.entity.entity_id = "climate.marketplace_fixture"
        entry = ConfigEntry(
            domain="haier_smartair2", version=2, minor_version=1, source="user",
            data={"local_ips": "001122334455:127.0.0.1"}, options={},
            title="Fixture AC", unique_id=None,
            discovery_keys=MappingProxyType({}), subentries_data=None,
        )
        self.hass.config_entries._entries[entry.entry_id] = entry
        async with asyncio.timeout(10):
            self.assertTrue(await ha_climate.async_setup(self.hass, {}))
        component = self.hass.data[DATA_COMPONENT]
        platform = component._async_init_entity_platform("haier_smartair2", "haier_smartair2", product)
        platform.config_entry = entry
        async with asyncio.timeout(10):
            await platform.async_add_entities([self.entity])
        self.assertIsNotNone(self.hass.states.get(self.entity.entity_id))

    async def asyncTearDown(self):
        await self.hass.async_stop(force=True)

    def test_native_values_and_identity_are_unchanged(self):
        self.assertEqual(self.entity.native_temperature_unit, "°C")
        self.assertEqual(self.entity.native_current_temperature, 20.5)
        self.assertEqual(self.entity.native_target_temperature, 22.0)
        self.assertEqual(self.entity.unique_id, "haier_smartair2_001122334455")

    def test_celsius_state_and_limits(self):
        state = self.hass.states.get(self.entity.entity_id)
        self.assertEqual(state.attributes["temperature_unit"], "°C")
        self.assertEqual(state.attributes["current_temperature"], 20.5)
        self.assertEqual(state.attributes["temperature"], 22.0)
        self.assertEqual(state.attributes["min_temp"], 16.0)
        self.assertEqual(state.attributes["max_temp"], 30.0)

    def test_fahrenheit_state_is_converted_once(self):
        self.hass.config.units = US_CUSTOMARY_SYSTEM
        self.entity.async_write_ha_state()
        state = self.hass.states.get(self.entity.entity_id)
        self.assertEqual(state.attributes["temperature_unit"], "°F")
        self.assertEqual(state.attributes["current_temperature"], 69.0)
        self.assertEqual(state.attributes["temperature"], 72.0)
        self.assertEqual(state.attributes["min_temp"], 61.0)
        self.assertEqual(state.attributes["max_temp"], 86.0)
        self.assertEqual(self.entity.native_target_temperature, 22.0)

    async def test_celsius_service_keeps_native_command(self):
        await self.hass.services.async_call("climate", "set_temperature", {
            "entity_id": self.entity.entity_id, "temperature": 24.0,
        }, blocking=True)
        self.coordinator.async_apply.assert_awaited_once_with(target_temp=24.0, power=True)

    async def test_fahrenheit_service_converts_to_native_celsius(self):
        self.hass.config.units = US_CUSTOMARY_SYSTEM
        await self.hass.services.async_call("climate", "set_temperature", {
            "entity_id": self.entity.entity_id, "temperature": 75.2,
        }, blocking=True)
        self.coordinator.async_apply.assert_awaited_once_with(target_temp=24.0, power=True)

    async def test_out_of_range_service_does_not_send_device_command(self):
        for units, temperature in ((METRIC_SYSTEM, 15), (METRIC_SYSTEM, 31),
                                   (US_CUSTOMARY_SYSTEM, 50), (US_CUSTOMARY_SYSTEM, 95)):
            with self.subTest(units=units.temperature_unit, temperature=temperature):
                self.hass.config.units = units
                with self.assertRaises(ServiceValidationError):
                    await self.hass.services.async_call("climate", "set_temperature", {
                        "entity_id": self.entity.entity_id, "temperature": temperature,
                    }, blocking=True)
        self.coordinator.async_apply.assert_not_awaited()

    def test_missing_readings_remain_unknown(self):
        self.coordinator.data = None
        self.assertIsNone(self.entity.native_current_temperature)
        self.assertIsNone(self.entity.native_target_temperature)
        self.assertIsNone(self.entity.state_attributes["current_temperature"])
        self.assertIsNone(self.entity.state_attributes["temperature"])


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    unittest.main()
