"""Isolated executable tests: no globally installed Home Assistant stubs."""
import asyncio
import importlib
import importlib.util
from pathlib import Path
import sys
import unittest
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
import builtins


def module(name, **attrs):
    value = ModuleType(name)
    value.__dict__.update(attrs)
    sys.modules[name] = value
    return value


class Generic:
    @classmethod
    def __class_getitem__(cls, _):
        return cls


class Flow:
    def __init_subclass__(cls, **kwargs):
        pass

    def async_show_form(self, **kwargs):
        return {"type": "form", **kwargs}

    def async_create_entry(self, **kwargs):
        return {"type": "create_entry", **kwargs}


class Marker:
    def __init__(self, schema, default=None):
        self.schema, self.default = schema, default


class Store(Generic):
    def __init__(self, *args, **kwargs):
        pass
    async def async_load(self):
        return []
    async def async_save(self, data):
        pass


class Coordinator(Generic):
    def __init__(self, *args, **kwargs):
        self.data = None
        self.config_entry = kwargs.get("config_entry")
    async def async_config_entry_first_refresh(self):
        self.data = await self._async_update_data()
    def async_set_updated_data(self, data):
        self.data = data
    def async_set_update_error(self, error):
        self.error = error


def install_stubs():
    module("homeassistant", __path__=[])
    module("homeassistant.config_entries", ConfigEntry=Generic, ConfigFlow=Flow,
           OptionsFlow=Flow, ConfigFlowResult=dict)
    module("homeassistant.core", HomeAssistant=object, callback=lambda f: f)
    module("homeassistant.const", Platform=SimpleNamespace(**{n:n.lower() for n in
           ("CLIMATE", "SENSOR", "BINARY_SENSOR", "SWITCH", "SELECT")}))
    module("homeassistant.exceptions", HomeAssistantError=RuntimeError, ConfigEntryNotReady=type("NotReady", (Exception,), {}))
    module("homeassistant.helpers", __path__=[])
    module("homeassistant.helpers.storage", Store=Store)
    module("homeassistant.helpers.update_coordinator", DataUpdateCoordinator=Coordinator, UpdateFailed=RuntimeError)
    module("homeassistant.helpers.device_registry", async_get=lambda hass: hass.registry)
    module("voluptuous", Schema=lambda schema:schema, Required=Marker, Optional=Marker)
    sys.path.insert(0, str(ROOT))


class OfflineTests(unittest.IsolatedAsyncioTestCase):
    async def test_import_and_configuration_never_load_cloud(self):
        install_stubs()
        original_import = builtins.__import__
        def guarded(name, *args, **kwargs):
            if any(word in name for word in ("cloud", "paho", "cryptography")):
                raise AssertionError(f"Forbidden cloud import: {name}")
            return original_import(name, *args, **kwargs)
        for name in tuple(sys.modules):
            if name.startswith("custom_components.haier_smartair2"):
                del sys.modules[name]
        with patch("builtins.__import__", side_effect=guarded), patch("socket.getaddrinfo", side_effect=AssertionError("DNS forbidden")), patch("socket.socket.connect", side_effect=AssertionError("Internet forbidden")):
            importlib.import_module("custom_components.haier_smartair2")
            flow = importlib.import_module("custom_components.haier_smartair2.config_flow")
            self.assertEqual(flow.HaierConfigFlow.VERSION, 2)
            user = flow.HaierConfigFlow()
            form = await user.async_step_user()
            self.assertEqual([k.schema for k in form["data_schema"]], ["local_ips"])
            valid = await user.async_step_user({"local_ips":"001122334455:10.0.0.2", "password":"discard"})
            self.assertEqual(valid["data"], {"local_ips":"001122334455:10.0.0.2"})
            invalid = await user.async_step_user({"local_ips":""})
            self.assertEqual(invalid["errors"], {"local_ips":"invalid_local_map"})
            options = flow.HaierOptionsFlow()
            options.config_entry = SimpleNamespace(data={}, options={})
            invalid = await options.async_step_init({"local_ips":"bad"})
            self.assertEqual(invalid["errors"], {"local_ips":"invalid_local_map"})
            valid = await options.async_step_init({"local_ips":"00:11:22:33:44:55:10.0.0.2", "region":"eu"})
            self.assertEqual(valid["data"], {"local_ips":"001122334455:10.0.0.2"})

ROOT = Path(__file__).resolve().parents[1]


class MigrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_migration_keeps_whole_field_options_precedence(self):
        install_stubs()
        integration = importlib.import_module("custom_components.haier_smartair2")
        cases = (
            ("001122334455:10.0.0.2", "", ""),
            ("obsolete invalid map", "001122334455:10.0.0.4", "001122334455:10.0.0.4"),
            ("001122334455:10.0.0.2", "repair me", "repair me"),
        )
        for old_map, option_map, expected in cases:
            with self.subTest(option_map=option_map):
                entry = SimpleNamespace(version=1, data={"local_ips": old_map}, options={"local_ips": option_map})
                hass = SimpleNamespace(config_entries=SimpleNamespace(
                    async_update_entry=lambda target, **changes: target.__dict__.update(changes)
                ))
                self.assertTrue(await integration.async_migrate_entry(hass, entry))
                self.assertEqual(entry.data, {"local_ips": expected})
                self.assertEqual(entry.options, {})

    async def test_migration_preserves_identity_uses_effective_map_and_removes_credentials(self):
        install_stubs()
        integration = importlib.import_module("custom_components.haier_smartair2")
        entry = SimpleNamespace(entry_id="keep-history", version=1, minor_version=1, unique_id="old-email",
            data={"username":"secret", "password":"secret", "client_id":"secret", "region":"eu",
                  "local_ips":"001122334455:10.0.0.2,AABBCCDDEEFF:10.0.0.3"},
            options={"region":"us", "local_ips":"001122334455:10.0.0.4"})
        def update(target, **kwargs):
            target.__dict__.update(kwargs)
        hass = SimpleNamespace(config_entries=SimpleNamespace(async_update_entry=Mock(side_effect=update)))
        with patch("socket.getaddrinfo", side_effect=AssertionError("DNS forbidden")), patch("socket.socket.connect", side_effect=AssertionError("Internet forbidden")):
            self.assertTrue(await integration.async_migrate_entry(hass, entry))
        self.assertEqual(entry.version, 2)
        self.assertEqual(entry.entry_id, "keep-history")
        self.assertEqual(entry.unique_id, "old-email")
        self.assertEqual(entry.data, {"local_ips":"001122334455:10.0.0.4"})
        self.assertEqual(entry.options, {})
        entry.version, entry.data, entry.options = 1, {"username":"old", "password":"secret"}, {}
        self.assertTrue(await integration.async_migrate_entry(hass, entry))
        self.assertEqual(entry.data, {"local_ips":""})


class RuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        install_stubs()
        self.integration = importlib.import_module("custom_components.haier_smartair2")
        self.codec = importlib.import_module("custom_components.haier_smartair2.codec")
        self.entry = SimpleNamespace(data={"local_ips":"001122334455:10.0.0.2,AABBCCDDEEFF:10.0.0.3"}, options={},
            entry_id="same-history", add_update_listener=Mock(return_value=lambda:None), async_on_unload=Mock())
        self.hass = SimpleNamespace(registry=SimpleNamespace(async_get_device=Mock(side_effect=lambda **kwargs:
            SimpleNamespace(name="Living room", name_by_user=None) if ("haier_smartair2", "001122334455") in kwargs["identifiers"] else None)),
            config_entries=SimpleNamespace(async_forward_entry_setups=AsyncMock(), async_unload_platforms=AsyncMock(return_value=True)))
        self.history = SimpleNamespace(async_load=AsyncMock(), async_flush=AsyncMock())
        self.clients = []
        outer = self
        class Local:
            def __init__(self, hass, ip, mac, history):
                self.mac, self.ip = mac, ip
                self.async_start, self.async_stop, self.async_poll = AsyncMock(), AsyncMock(), AsyncMock()
                outer.clients.append(self)
            def latest_frame(self, *args):
                size = 24 if self.mac == "001122334455" else 32
                return outer.codec.build_frame(2, b"\x6d\x01", bytes(size))
            def latest_big_frame(self, *args): return None
            def latest_alarm_bits(self): return None
            def add_listener(self, listener): return lambda:None
        self.Local = Local

    async def test_forward_failure_unloads_partial_platforms_and_cleans_runtime(self):
        self.hass.config_entries.async_forward_entry_setups.side_effect = RuntimeError("platform failed")
        with patch.object(self.integration, "HaierLocalClient", self.Local), patch.object(self.integration, "PacketHistory", return_value=self.history):
            with self.assertRaisesRegex(Exception, "platform failed"):
                await self.integration.async_setup_entry(self.hass, self.entry)
        for client in self.clients:
            client.async_stop.assert_awaited_once()
        self.history.async_flush.assert_awaited_once()
        self.hass.config_entries.async_unload_platforms.assert_awaited_once()
        self.assertIsNone(getattr(self.entry, "runtime_data", None))

    async def test_setup_failures_stop_all_clients_and_flush_history(self):
        for failure in ("missing", "unsupported", "connect", "cancel", "refresh"):
            with self.subTest(failure=failure):
                self.clients.clear()
                self.history.async_flush.reset_mock()
                outer = self
                class Broken(self.Local):
                    def __init__(self, *args):
                        super().__init__(*args)
                        if failure == "connect":
                            self.async_start.side_effect = OSError("offline")
                        if failure == "cancel":
                            self.async_start.side_effect = asyncio.CancelledError()
                    def latest_frame(self, *args):
                        if failure == "missing": return None
                        if failure == "unsupported": return outer.codec.build_frame(2, b"\x6d\x01", bytes(28))
                        return super().latest_frame(*args)
                refresh = AsyncMock(side_effect=RuntimeError("refresh failed"))
                with patch.object(self.integration, "HaierLocalClient", Broken), patch.object(self.integration, "PacketHistory", return_value=self.history), patch.object(self.integration, "FIRST_STATUS_TIMEOUT", 0.02):
                    if failure == "refresh":
                        with patch.object(self.integration.HaierCoordinator, "async_config_entry_first_refresh", refresh):
                            with self.assertRaisesRegex(Exception, "refresh failed"):
                                await self.integration.async_setup_entry(self.hass, self.entry)
                    else:
                        expected = asyncio.CancelledError if failure == "cancel" else Exception
                        with self.assertRaises(expected):
                            await self.integration.async_setup_entry(self.hass, self.entry)
                for client in self.clients: client.async_stop.assert_awaited_once()
                self.history.async_flush.assert_awaited_once()
                self.assertIsNone(getattr(self.entry, "runtime_data", None))

    async def test_missing_map_fails_actionably_before_opening_any_client(self):
        self.entry.data = {"local_ips":""}
        with patch.object(self.integration, "HaierLocalClient", self.Local):
            with self.assertRaisesRegex(Exception, "Configure.*Options"):
                await self.integration.async_setup_entry(self.hass, self.entry)
        self.assertEqual(self.clients, [])

    async def test_setup_waits_for_a_late_first_status(self):
        class Late(self.Local):
            calls = 0
            def latest_frame(self, *args):
                self.calls += 1
                if self.calls < 3: return None
                return super().latest_frame(*args)
        with patch.object(self.integration, "HaierLocalClient", Late), patch.object(self.integration, "PacketHistory", return_value=self.history):
            self.assertTrue(await self.integration.async_setup_entry(self.hass, self.entry))
        self.assertTrue(all(c.calls >= 3 for c in self.clients))

    async def test_coordinator_is_bound_to_config_entry_for_framework_first_refresh(self):
        with patch.object(self.integration, "HaierLocalClient", self.Local), patch.object(self.integration, "PacketHistory", return_value=self.history):
            await self.integration.async_setup_entry(self.hass, self.entry)
        self.assertTrue(all(c.config_entry is self.entry for c in self.entry.runtime_data.coordinators))

    async def test_setup_prefers_entry_scoped_device_registry_lookup(self):
        registry = self.hass.registry
        registry.async_get_device_by_identifier = Mock(return_value=SimpleNamespace(name="Original name", name_by_user="User label"))
        registry.async_get_device.side_effect = AssertionError("Deprecated lookup must not be used")
        with patch.object(self.integration, "HaierLocalClient", self.Local), patch.object(self.integration, "PacketHistory", return_value=self.history):
            self.assertTrue(await self.integration.async_setup_entry(self.hass, self.entry))
        registry.async_get_device_by_identifier.assert_any_call(("haier_smartair2", "001122334455"), "same-history")
        self.assertEqual(self.entry.runtime_data.coordinators[0].dev_name, "Original name")

    async def test_setup_uses_local_map_and_preserves_registry_name_and_identity(self):
        with patch.object(self.integration, "HaierLocalClient", self.Local), patch.object(self.integration, "PacketHistory", return_value=self.history), patch("socket.getaddrinfo", side_effect=AssertionError("DNS forbidden")), patch("socket.socket.connect", side_effect=AssertionError("Internet forbidden")):
            self.assertTrue(await self.integration.async_setup_entry(self.hass, self.entry))
        coords = self.entry.runtime_data.coordinators
        self.assertEqual([c.devid for c in coords], ["001122334455", "AABBCCDDEEFF"])
        self.assertEqual([c.dev_name for c in coords], ["Living room", "Haier AABBCCDDEEFF"])
        self.assertIsInstance(coords[0].codec, self.codec.CodecV2)
        self.assertIsInstance(coords[1].codec, self.codec.CodecV3)
        self.assertTrue(all(c.via_cloud is False for c in coords))
        self.assertEqual([c.ip for c in self.clients], ["10.0.0.2", "10.0.0.3"])
        self.assertTrue(await self.integration.async_unload_entry(self.hass, self.entry))
        for client in self.clients: client.async_stop.assert_awaited_once()
        self.history.async_flush.assert_awaited_once()


class PackagingTests(unittest.TestCase):
    def test_cloud_implementation_and_constants_are_removed(self):
        self.assertFalse((ROOT / "custom_components/haier_smartair2/cloud.py").exists())
        install_stubs()
        const = importlib.import_module("custom_components.haier_smartair2.const")
        for name in ("LOGIN_HOST", "REGIONS", "DEFAULT_REGION", "MASTER_GW_PORT", "APP_KEY", "AUTH_SALT", "generate_client_id", "TOKEN_REFRESH_SECONDS"):
            self.assertFalse(hasattr(const, name), name)

    def test_all_localized_forms_are_local_only(self):
        import json
        for language in ("en", "pt", "pl"):
            text = json.loads((ROOT / f"custom_components/haier_smartair2/translations/{language}.json").read_text())
            self.assertIn("entity", text)
            for section, step in (("config", "user"), ("options", "init")):
                self.assertEqual(set(text[section]["step"][step]["data"]), {"local_ips"})
                self.assertIn("invalid_local_map", text[section]["error"])
            self.assertNotIn("selector", text)


class MapTests(unittest.TestCase):
    def test_map_validation(self):
        spec = importlib.util.spec_from_file_location("local_map", ROOT / "custom_components/haier_smartair2/local_map.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        self.assertEqual(mod.parse_local_map("2c:37:c5:0b:54:4a:192.168.1.2,001122334455:10.0.0.2"),
                         {"2C37C50B544A": "192.168.1.2", "001122334455": "10.0.0.2"})
        for raw in (None, "", " ", "garbage", "GG1122334455:10.0.0.2", "001122334455:haier.example",
                    "001122334455:256.1.1.1", "00:11:2233:44:55:10.0.0.2", "001122334455:10.0.0.2,",
                    "001122334455:10.0.0.2,00:11:22:33:44:55:10.0.0.3",
                    "001122334455:10.0.0.2,AABBCCDDEEFF:10.0.0.2", "001122334455:0.0.0.0",
                    "001122334455:224.0.0.1", "001122334455:255.255.255.255"):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                mod.parse_local_map(raw)


if __name__ == "__main__":
    unittest.main(verbosity=2)
