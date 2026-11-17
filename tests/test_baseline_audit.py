"""Retained/reconstructed offline audit probes rerun against the exact baseline.

These tests PASS when historical BUGS are observed, not when today's product is
fixed. Current local-only guard tests independently check cloud removal. No
production module (or HA, MQTT, HTTP or crypto dependency) is imported here.
Only selected definitions from `git show PINNED_SHA:path` are executed; all
network/HA boundaries are bounded fakes. This is not an earlier execution log.
"""
from __future__ import annotations

import ast
import asyncio
from dataclasses import dataclass
from functools import lru_cache
import logging
from pathlib import Path
import ssl
import struct
import subprocess
from types import SimpleNamespace
from typing import Any
import unittest
from unittest.mock import AsyncMock, Mock
import json

ROOT = Path(__file__).resolve().parents[1]
PINNED_SHA = "5b77363a05225311fb85ef89eb16136b26440acd"
PREFIX = "custom_components/haier_smartair2/"
LOGGER = logging.getLogger(__name__)
NORMAL = bytes.fromhex(
    "ffff2a400000000000026d01060a850002010000000029004e00000300000000000000000000000000000000ec4268"
)


@lru_cache(maxsize=None)
def baseline_tree(filename):
    result = subprocess.run(
        ["git", "show", f"{PINNED_SHA}:{PREFIX}{filename}"],
        cwd=ROOT, text=True, capture_output=True, timeout=10,
    )
    if result.returncode:
        raise AssertionError(
            f"Historical audit requires pinned baseline {PINNED_SHA}:{PREFIX}{filename}. "
            "Fetch repository history (CI checkout fetch-depth: 0; locally git fetch "
            f"--unshallow or git fetch origin {PINNED_SHA}). Do not skip this audit. "
            + result.stderr
        )
    return ast.parse(result.stdout, filename=f"{PINNED_SHA}:{filename}")


def selected(filename, names, owner=None, namespace=None):
    """Execute exact, unmodified AST definitions, never the original imports."""
    body = baseline_tree(filename).body
    if owner:
        body = next(n.body for n in body if isinstance(n, ast.ClassDef) and n.name == owner)
    nodes = [n for n in body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
             and n.name in names]
    found = {n.name for n in nodes}
    if found != set(names):
        raise AssertionError(f"Missing pinned definitions: {set(names) - found}")
    env = {"__name__": __name__, "_LOGGER": LOGGER, **(namespace or {})}
    module = ast.Module(body=[ast.ImportFrom(module="__future__", names=[
        ast.alias(name="annotations")], level=0), *nodes], type_ignores=[])
    exec(compile(ast.fix_missing_locations(module), f"{PINNED_SHA}:{filename}", "exec"), env)
    return env


def pinned_codec() -> Any:
    # Only literal protocol constants and the actual codec methods/helpers needed
    # to observe the command bytes, not a fake implementation of the protocol.
    env = {"dataclass": dataclass, "__name__": __name__}
    for filename, wanted in (("const.py", lambda name: name.startswith(("MODE_", "FAN_"))),
                             ("codec.py", lambda name: name.startswith("_V3_") or name == "_SOURCE")):
        nodes: list[ast.stmt] = [n for n in baseline_tree(filename).body if isinstance(n, ast.Assign)
                 and any(isinstance(t, ast.Name) and wanted(t.id) for t in n.targets)]
        exec(compile(ast.Module(body=nodes, type_ignores=[]), filename, "exec"), env)
    env = selected("codec.py", ["HaierState", "_checksum", "build_frame", "extract_block",
                                "_temp64", "_set_bit"], namespace=env)
    methods = selected("codec.py", ["decode", "encode_set"], "CodecV3", env)
    return type("PinnedCodec", (), {name: methods[name] for name in ("decode", "encode_set")})()


def coordinator(transport, codec, via_cloud) -> Any:
    methods = selected("coordinator.py", ["_decode_latest", "_on_push", "async_apply"],
                       "HaierCoordinator", {"asyncio": asyncio, "UpdateFailed": RuntimeError})
    obj: Any = type("PinnedCoordinator", (), {name: methods[name]
               for name in ("_decode_latest", "_on_push", "async_apply")})()
    obj.transport, obj.codec, obj.via_cloud = transport, codec, via_cloud
    obj.devid, obj.data, obj._last_fixed_swing = "001122334455", None, None
    obj.async_set_updated_data = lambda value: setattr(obj, "data", value)
    obj.async_set_update_error = Mock()
    obj.async_request_refresh = AsyncMock()
    return obj


class BaselineCloudAuditTests(unittest.IsolatedAsyncioTestCase):
    def test_bug_tls_peer_and_hostname_checks_disabled(self):
        ctx = selected("cloud.py", ["_insecure_ctx"], namespace={"ssl": ssl})["_insecure_ctx"]()
        self.assertFalse(ctx.check_hostname)
        self.assertEqual(ctx.verify_mode, ssl.CERT_NONE)

    def test_bug_gateway_eof_retries_forever_until_explicit_sentinel(self):
        class EofSentinel(Exception):
            pass

        class ClosedSocket:
            calls = 0

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def sendall(self, data):
                pass

            def recv(self, size):
                self.calls += 1
                if self.calls == 5:
                    raise EofSentinel("bounded audit: four EOF reads did not exit")
                return b""

        sock = ClosedSocket()
        connect = Mock(return_value=sock)
        env = selected("cloud.py", ["_master_gw_blocking"], "HaierCloudClient", {
            "json": json, "struct": struct, "MASTER_GW_PORT": 443,
            "socket": SimpleNamespace(create_connection=connect),
            "_insecure_ctx": lambda: SimpleNamespace(wrap_socket=lambda *a, **k: sock),
        })
        with self.assertRaisesRegex(EofSentinel, "four EOF reads"):
            env["_master_gw_blocking"](SimpleNamespace(_app_client_id="audit", _gateway="example.invalid"))
        self.assertEqual(sock.calls, 5)
        connect.assert_called_once_with(("example.invalid", 443), timeout=8)

    async def test_bug_device_api_error_json_is_silently_empty_list(self):
        class Response:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return False

            async def json(self, **kwargs):
                return {"retCode": "10001", "retInfo": "token expired"}

        post = Mock(return_value=Response())
        env = selected("cloud.py", ["async_get_devices"], "HaierCloudClient", {
            **{name: "audit" for name in ("APP_KEY", "APP_ID", "APP_VERSION", "REST_CLIENT_ID",
                                          "LOGIN_HOST", "LOGIN_PORT")},
            "json": json, "async_get_clientsession": lambda hass: SimpleNamespace(post=post),
        })
        self.assertEqual(await env["async_get_devices"](SimpleNamespace(_token="audit", _hass=None)), [])
        self.assertFalse(post.call_args.kwargs["ssl"])

    async def test_bug_login_http_tls_verification_disabled(self):
        class Response:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return False

            async def json(self, **kwargs):
                return {"retCode": "00000", "accessToken": "offline-audit-token"}

        post = Mock(return_value=Response())
        env = selected("cloud.py", ["async_login"], "HaierCloudClient", {
            **{name: "audit" for name in ("APP_KEY", "APP_ID", "APP_VERSION", "REST_CLIENT_ID",
                                          "LOGIN_HOST", "LOGIN_PORT")},
            "json": json, "async_get_clientsession": lambda hass: SimpleNamespace(post=post),
        })
        client = SimpleNamespace(_username="fake", _password="fake", _hass=None)
        self.assertEqual(await env["async_login"](client), "offline-audit-token")
        self.assertFalse(post.call_args.kwargs["ssl"])

    def test_bug_disconnect_keeps_cached_status_and_coordinator_ignores_offline(self):
        env = selected("cloud.py", ["_on_disconnect", "latest_frame", "is_online"], "HaierCloudClient")
        cloud_type = type("PinnedCloud", (), {name: env[name] for name in (
            "_on_disconnect", "latest_frame", "is_online")})
        schedule = Mock()  # Record reconnect scheduling; never run a background task.
        cloud: Any = cloud_type()
        cloud._stopped = False
        cloud._hass = SimpleNamespace(loop=SimpleNamespace(call_soon_threadsafe=schedule))
        codec = pinned_codec()
        frame = NORMAL  # A real captured status, not an outbound command frame.
        cloud._frames = {"001122334455": frame}
        cloud._online = {"001122334455": True}
        cloud._on_disconnect(None, None, None, 1)
        self.assertIs(cloud.latest_frame("001122334455"), frame)
        self.assertTrue(cloud.is_online("001122334455"))  # stale online bit survives too
        schedule.assert_called_once()
        cloud._online["001122334455"] = False
        coord = coordinator(cloud, codec, True)
        coord._on_push()
        self.assertIsNotNone(coord.data)
        self.assertTrue(coord.data.power)
        coord.async_set_update_error.assert_not_called()

    async def test_bug_setup_cloud_not_stopped_when_local_first_refresh_fails(self):
        events = []

        class RefreshFailure(Exception):
            pass

        class Cloud:
            async def async_get_devices(self):
                return [{"id": "LOCAL"}, {"id": "CLOUD"}]

            def register_device(self, devid):
                pass

            async def async_start(self):
                events.append("cloud-start")

            async def async_stop(self):
                events.append("cloud-stop")

        class Local:
            async def async_start(self):
                events.append("local-start")

            async def async_poll(self, devid):
                pass

            async def async_stop(self):
                events.append("local-stop")

        class History:
            async def async_load(self):
                pass

            async def async_flush(self):
                events.append("history-flush")

        class Coord:
            def __init__(self, *args, via_cloud):
                self.via_cloud = via_cloud

            async def async_config_entry_first_refresh(self):
                events.append("cloud-refresh" if self.via_cloud else "local-refresh-fails")
                raise RefreshFailure("injected HA local first-refresh failure")

        cloud, local, history = Cloud(), Local(), History()
        env = selected("__init__.py", ["async_setup_entry"], namespace={
            "asyncio": asyncio, "CONF_REGION": "region", "DEFAULT_REGION": "eu",
            "REGIONS": {"eu": "example.invalid"}, "CONF_LOCAL_IPS": "local_ips",
            "CONF_CLIENT_ID": "client_id", "CONF_USERNAME": "username", "CONF_PASSWORD": "password",
            "_parse_local_map": lambda raw: {"LOCAL": "192.0.2.1"},
            "HaierCloudClient": lambda *args: cloud, "CloudAuthError": type("CloudAuthError", (Exception,), {}),
            "ConfigEntryNotReady": RuntimeError, "PacketHistory": lambda store: history,
            "history_store": lambda *args: None,
            "HaierData": lambda **kwargs: SimpleNamespace(**kwargs, local_clients=[], coordinators=[]),
            "HaierLocalClient": lambda *args: local, "HaierCoordinator": Coord,
            "codec_for_type": lambda kind: None,
        })
        entry = SimpleNamespace(data={"client_id": "audit", "username": "fake", "password": "fake"},
                                options={}, entry_id="audit")
        with self.assertRaisesRegex(RefreshFailure, "local first-refresh"):
            await env["async_setup_entry"](SimpleNamespace(), entry)
        self.assertEqual(events, ["local-start", "cloud-start", "local-refresh-fails",
                                  "local-stop", "history-flush"])
        self.assertNotIn("cloud-stop", events)
        self.assertFalse(hasattr(entry, "runtime_data"))

    async def test_bug_concurrent_commands_overwrite_previous_full_snapshot(self):
        codec = pinned_codec()
        initial = NORMAL  # Health=False, display=True in the baseline AS35 capture.
        sent = []
        both_sent = asyncio.Event()

        async def send(devid, frame):
            sent.append(codec.decode(frame))
            if len(sent) == 2:
                both_sent.set()
            await both_sent.wait()  # Force actual overlap, independent of scheduler timing.

        transport = SimpleNamespace(latest_frame=lambda devid: initial,
                                    latest_alarm_bits=lambda: None, async_send_frame=send)
        coord = coordinator(transport, codec, False)
        await asyncio.wait_for(asyncio.gather(coord.async_apply(health=True),
                                              coord.async_apply(display=False)), timeout=3)
        self.assertEqual(len(sent), 2)
        self.assertEqual([(s.health, s.display) for s in sent], [(True, True), (False, False)])
        self.assertEqual(coord.async_request_refresh.await_count, 2)

    async def test_bug_combined_hvac_off_temperature_command_powers_on(self):
        env = selected("climate.py", ["async_set_temperature"], "HaierClimate",
                       {"ATTR_TEMPERATURE": "temperature"})
        apply = AsyncMock()
        await env["async_set_temperature"](SimpleNamespace(coordinator=SimpleNamespace(async_apply=apply)),
                                           temperature=24, hvac_mode="off")
        apply.assert_awaited_once_with(target_temp=24.0, power=True)


if __name__ == "__main__":
    unittest.main()
