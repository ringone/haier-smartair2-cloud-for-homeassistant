"""Regression checks for the AS35 captures, diagnostics and local read path."""

import asyncio
from dataclasses import asdict
from importlib import import_module
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

# Import the protocol modules without starting Home Assistant.
ROOT = Path(__file__).resolve().parents[1]
DOMAIN = "haier_smartair2"


def module(name, **attributes):
    result = ModuleType(name)
    result.__dict__.update(attributes)
    sys.modules[name] = result


class FakeStore:
    def __init__(self, records=None):
        self.saved = records
        self.pending = None

    @classmethod
    def __class_getitem__(cls, _):
        return cls

    async def async_load(self):
        return self.saved

    def async_delay_save(self, snapshot, delay):
        self.pending = snapshot

    async def async_save(self, snapshot):
        self.saved = json.loads(json.dumps(snapshot))
        self.pending = None


module("homeassistant", __path__=[])
module("homeassistant.core", HomeAssistant=object, callback=lambda func: func)
module("homeassistant.const", Platform=SimpleNamespace(**{
    name: name.lower() for name in ("CLIMATE", "SENSOR", "BINARY_SENSOR", "SWITCH", "SELECT")
}))
module("homeassistant.exceptions", HomeAssistantError=type("HomeAssistantError", (Exception,), {}))
module("homeassistant.helpers", __path__=[])
module("homeassistant.helpers.storage", Store=FakeStore)
module("homeassistant.helpers.device_registry", DeviceEntry=object, DeviceInfo=lambda **data: data)
module("homeassistant.helpers.entity", EntityCategory=SimpleNamespace(DIAGNOSTIC="diagnostic"))
module("homeassistant.helpers.entity_platform", AddEntitiesCallback=object)


class FakeCoordinator:
    @classmethod
    def __class_getitem__(cls, _):
        return cls

    def __init__(self, coordinator=None, *args, **kwargs):
        self.coordinator = coordinator
        self.data = None

    def async_set_updated_data(self, data):
        self.data = data

    def async_set_update_error(self, error):
        self.error = error


module("homeassistant.helpers.update_coordinator", CoordinatorEntity=FakeCoordinator,
       DataUpdateCoordinator=FakeCoordinator, UpdateFailed=RuntimeError)
module("homeassistant.components", __path__=[])
module("homeassistant.components.binary_sensor", BinarySensorEntity=type("BinarySensorEntity", (), {}),
       BinarySensorDeviceClass=SimpleNamespace(PROBLEM="problem", RUNNING="running"))
module(DOMAIN, __path__=[str(ROOT / "custom_components" / DOMAIN)], HaierConfigEntry=object)
codec = import_module(f"{DOMAIN}.codec")
history = import_module(f"{DOMAIN}.packet_history")
transport = import_module(f"{DOMAIN}.local")
coordinator = import_module(f"{DOMAIN}.coordinator")
diagnostics = import_module(f"{DOMAIN}.diagnostics")
sensors = import_module(f"{DOMAIN}.binary_sensor")

ALARM = bytes.fromhex("ffff12400000000000040f5a0000000000000000bf0a33")
NORMAL = bytes.fromhex("ffff2a400000000000026d01060a850002010000000029004e00000300000000000000000000000000000000ec4268")
EXTENDED = bytes.fromhex("ffff38400000000000027d01060a850002010000000029004e0000030000000000000000000000000000000000007c7e0000462801ff5502250058462efc")
EXTENDED_SECOND = bytes.fromhex("ffff38400000000000027d01060685000201000000002b004e00000300000000000000000000000000000000000058800000530101ff550225005808b98a")
DEVICE = "001122334455"


def envelope(payload):
    header = bytearray(80)
    header[2:4] = b"\x27\x15"
    header[40:52] = DEVICE.encode()
    header[79] = len(payload)
    return bytes(header) + payload


class DecodeTests(unittest.TestCase):
    def test_real_temperatures_and_actuators(self):
        v3 = codec.CodecV3()
        for payload, expected in (
            (EXTENDED, (20.5, 42.0, 62.0, 6.0, 40.0)),
            (EXTENDED_SECOND, (21.5, 24.0, 64.0, 19.0, 1.0)),
        ):
            frame = codec.parse_local_frame(payload)
            state = v3.decode(frame).merged(**v3.decode_big(frame))
            self.assertEqual(
                (state.current_temp, state.indoor_coil_temp, state.outdoor_out_temp,
                 state.defrost_temp, state.compressor_hz), expected
            )
            self.assertEqual((state.target_temp, state.outdoor_temp, state.expansion_valve),
                             (22.0, 14.0, 88.0))
            self.assertTrue(state.compressor_on and state.indoor_fan_on)
            self.assertIs(state.defrost_on, False)
            self.assertIs(state.indoor_electric_heat_on, False)
            for field in ("outdoor_fan", "four_way_valve", "outdoor_coil_temp",
                          "outdoor_in_temp", "compressor_current"):
                self.assertIsNone(getattr(state, field))

    def test_other_two_bit_values(self):
        frame = codec.parse_local_frame(EXTENDED)
        _, raw = codec.extract_block(frame)
        modified = raw[:42] + bytes.fromhex("06d0") + raw[44:]
        state = codec.CodecV3().decode_big(codec.build_frame(2, b"\x7d\x01", modified))
        self.assertIs(state["compressor_on"], False)
        self.assertIs(state["indoor_fan_on"], False)
        self.assertIsNone(state["indoor_electric_heat_on"])
        self.assertIs(state["defrost_on"], True)

    def test_alarm_bitmap_and_shape(self):
        self.assertEqual(codec.decode_alarm_bits(codec.parse_local_frame(ALARM)), ())
        payload = ((1 << 63) | (1 << 15) | (1 << 8) | 1).to_bytes(8, "big")
        self.assertEqual(codec.decode_alarm_bits(codec.build_frame(4, b"\x0f\x5a", payload)),
                         (0, 8, 15, 63))
        for frame in (codec.build_frame(4, b"\x0f\x5a", payload[1:]), NORMAL):
            with self.assertRaises(ValueError):
                codec.decode_alarm_bits(frame)


class HistoryTests(unittest.IsolatedAsyncioTestCase):
    async def test_capture_reload_sampling_redaction_and_retention(self):
        store = FakeStore()
        capture = history.PacketHistory(store)
        now = 2_000_000.0
        other = codec.build_frame(2, b"\x6c\x01", b"PRIVATE")
        bad = NORMAL[:-1]
        with patch.object(history, "time", side_effect=lambda: now):
            await capture.async_load()
            for raw, logical, error in (
                (EXTENDED, codec.parse_local_frame(EXTENDED), None),
                (EXTENDED, codec.parse_local_frame(EXTENDED), None),
                (ALARM, ALARM, None),
                (ALARM, ALARM, None),
                (other, other, None),
                (bad, None, "invalid smartair2 frame length"),
            ):
                capture.record(DEVICE, raw, logical, error)
            capture.record("another-device", NORMAL, NORMAL)
            now += history.SAMPLE_INTERVAL
            capture.record(DEVICE, EXTENDED, codec.parse_local_frame(EXTENDED))
            await capture.async_flush()
            self.assertEqual(len(store.saved), 7)
            self.assertEqual(store.saved[3]["payload_hex"], other.hex())
            self.assertEqual(store.saved[4]["payload_hex"], bad.hex())
            reloaded = history.PacketHistory(store)
            await reloaded.async_load()
            entry = SimpleNamespace(runtime_data=SimpleNamespace(packet_history=reloaded))
            result = await diagnostics.async_get_device_diagnostics(
                None, entry, SimpleNamespace(identifiers={(DOMAIN, DEVICE)})
            )
            frames = result["local_packets"]
            self.assertEqual(len(frames), 6)
            self.assertEqual(frames[0]["epp_hex"], EXTENDED.hex())
            self.assertEqual(frames[1]["epp_hex"], ALARM.hex())
            self.assertIsNone(frames[3]["epp_hex"])
            self.assertIsNone(frames[4]["epp_hex"])
            self.assertIn("invalid", frames[4]["validation_error"])
            self.assertNotIn(DEVICE, json.dumps(result))
            now += history.RETENTION_SECONDS + 1
            self.assertEqual(reloaded.diagnostics(), [])
            await reloaded.async_flush()
            self.assertEqual(store.saved, [])

    async def test_bounded_history(self):
        store = FakeStore()
        with patch.object(history, "MAX_RECORDS", 2):
            capture = history.PacketHistory(store)
            for raw in (NORMAL, ALARM, EXTENDED):
                capture.record(DEVICE, raw, codec.parse_local_frame(raw))
            await capture.async_flush()
        self.assertEqual([r["payload_hex"] for r in store.saved], [ALARM.hex(), EXTENDED.hex()])

    async def test_local_loop_updates_and_discards_old_alarms(self):
        store = FakeStore()
        capture = history.PacketHistory(store)
        reader = asyncio.StreamReader()
        writer = MagicMock()
        writer.is_closing.return_value = False
        client = transport.HaierLocalClient(None, "example.invalid", DEVICE, capture)
        client._writer = writer
        coord = coordinator.HaierCoordinator(None, client, codec.CodecV3(), DEVICE, "Test", False)
        states = []
        client.add_listener(lambda: states.append(asdict(coord.data) if client.is_online() else None))
        alarm_with_bit = codec.build_frame(4, b"\x0f\x5a", bytes(7) + b"\x01")
        reader.feed_data(b"".join(map(envelope, (ALARM, NORMAL, EXTENDED, alarm_with_bit, ALARM))))
        reader.feed_eof()
        await client._read_loop(reader, writer)
        self.assertEqual([s["alarm_bits"] for s in states[1:-1]], [(), (), (0,), ()])
        self.assertTrue(states[2]["compressor_on"])
        self.assertIsNone(states[-1])
        self.assertIsNone(client.latest_alarm_bits())
        writer.close.assert_called_once()
        await capture.async_flush()
        self.assertEqual(len(store.saved), 5)

    async def test_binary_sensors_unknown_and_alarm_clear(self):
        local = SimpleNamespace(devid=DEVICE, codec=codec.CodecV3(), via_cloud=False, data=None)
        cloud = SimpleNamespace(devid="cloud", codec=codec.CodecV3(), via_cloud=True, data=None)
        add = MagicMock()
        await sensors.async_setup_entry(None, SimpleNamespace(
            runtime_data=SimpleNamespace(coordinators=[local, cloud])
        ), add)
        entities = add.call_args.args[0]
        by_key = {entity._attr_translation_key: entity for entity in entities
                  if DEVICE in entity._attr_unique_id}
        self.assertEqual(len(entities), 9)
        self.assertEqual(by_key["filter"]._attr_unique_id, f"{DOMAIN}_{DEVICE}_filter_change")
        alarm = by_key["active_alarms"]
        self.assertIsNone(alarm.is_on)
        local.data = codec.HaierState(compressor_on=False, alarm_bits=(63,))
        self.assertIs(by_key["compressor"].is_on, False)
        self.assertTrue(alarm.is_on)
        self.assertEqual(alarm.extra_state_attributes, {"active_alarm_bits": [63]})
        local.data.alarm_bits = ()
        self.assertIs(alarm.is_on, False)
        self.assertIsNone(by_key["outdoor_fan"].is_on)
        self.assertFalse(by_key["outdoor_fan"]._attr_entity_registry_enabled_default)


if __name__ == "__main__":
    unittest.main()
