"""Local transport: direct TCP 56800 for plaintext-dongle devices.

Wraps smartair2 frames in the 80-byte uSDK LAN envelope (marker 0x2714 out /
0x2715 in, MAC as ASCII at [40:52], seq at [75], payload length at [79]).
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from time import monotonic

from homeassistant.core import HomeAssistant

from .codec import BIG_POLL_FRAME, POLL_FRAME, decode_alarm_bits, parse_local_frame
from .const import LOCAL_PORT
from .packet_history import PacketHistory

_LOGGER = logging.getLogger(__name__)

MARKER_TX = 0x2714
MARKER_RX = 0x2715
CONNECT_TIMEOUT = 10
POLL_INTERVAL = 12
FRAME_TIMEOUT = 40
_STATUS_SUB = b"\x6d\x01"
_BIG_SUB = b"\x7d\x01"


def _normalise_mac(mac: str) -> str:
    cleaned = "".join(c for c in mac if c.isalnum()).upper()
    if len(cleaned) != 12:
        raise ValueError(f"MAC must have 12 hex chars: {mac!r}")
    return cleaned


def _envelope(payload: bytes, mac: str, seq: int) -> bytes:
    env = bytearray(80)
    env[2:4] = MARKER_TX.to_bytes(2, "big")
    env[40:52] = mac.encode("ascii")
    env[75] = seq & 0xFF
    env[79] = len(payload)
    return bytes(env) + payload


class HaierLocalClient:
    """Persistent TCP connection to one local device."""

    def __init__(
        self, hass: HomeAssistant, ip: str, mac: str, history: PacketHistory
    ) -> None:
        self._hass = hass
        self._ip = ip
        self._mac = _normalise_mac(mac)
        self._history = history
        self._alarm_bits: tuple[int, ...] | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._read_task: asyncio.Task | None = None
        self._keepalive_task: asyncio.Task | None = None
        self._seq = 0
        self._frame: bytes | None = None
        self._big_frame: bytes | None = None
        self._frame_at = self._big_frame_at = 0.0
        self._listeners: list[Callable[[], None]] = []
        self._stopped = False
        self._lock = asyncio.Lock()

    def add_listener(self, cb: Callable[[], None]) -> Callable[[], None]:
        self._listeners.append(cb)

        def remove() -> None:
            if cb in self._listeners:
                self._listeners.remove(cb)

        return remove

    def latest_frame(self, _devid: str | None = None) -> bytes | None:
        return self._frame if monotonic() - self._frame_at < FRAME_TIMEOUT else None

    def latest_big_frame(self, _devid: str | None = None) -> bytes | None:
        return self._big_frame if monotonic() - self._big_frame_at < FRAME_TIMEOUT else None

    def latest_alarm_bits(self) -> tuple[int, ...] | None:
        """Return the last alarm report from the current connection."""
        return self._alarm_bits

    def is_online(self, _devid: str | None = None) -> bool:
        return self._writer is not None and not self._writer.is_closing()

    def _notify(self) -> None:
        for cb in list(self._listeners):
            try:
                cb()
            except Exception:  # noqa: BLE001
                _LOGGER.exception("listener failed")

    @property
    def _next_seq(self) -> int:
        self._seq = (self._seq + 1) % 256
        return self._seq

    async def async_start(self) -> None:
        await self._connect()
        if self._keepalive_task is None:
            self._keepalive_task = self._hass.async_create_background_task(
                self._keepalive_loop(), f"haier_local_keepalive_{self._ip}"
            )

    async def _connect(self) -> asyncio.StreamWriter:
        async with self._lock:
            if self._stopped:
                raise ConnectionError("Haier local client is stopped")
            if self._writer is not None and not self._writer.is_closing():
                return self._writer
            if self._writer is not None:
                self._disconnect(self._writer)
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self._ip, LOCAL_PORT), CONNECT_TIMEOUT
            )
            if self._stopped:
                writer.close()
                raise ConnectionError("Haier local client is stopped")
            self._writer = writer
            self._read_task = self._hass.async_create_background_task(
                self._read_loop(reader, writer), f"haier_local_read_{self._ip}"
            )
            return writer

    async def _keepalive_loop(self) -> None:
        while not self._stopped:
            await asyncio.sleep(POLL_INTERVAL)
            try:
                await self.async_poll()
            except (OSError, TimeoutError) as err:
                _LOGGER.debug("Haier local poll for %s failed: %s", self._ip, err)

    def _disconnect(self, writer: asyncio.StreamWriter) -> None:
        if self._writer is not writer:
            return
        self._writer = None
        self._frame = self._big_frame = None
        self._alarm_bits = None
        self._frame_at = self._big_frame_at = 0.0
        writer.close()
        if self._read_task is not None and self._read_task is not asyncio.current_task():
            self._read_task.cancel()
        if not self._stopped:
            self._notify()

    async def _read_loop(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        status_deadline = monotonic() + FRAME_TIMEOUT
        try:
            while self._writer is writer:
                remaining = status_deadline - monotonic()
                if remaining <= 0:
                    raise TimeoutError("No valid Haier local status frame")
                async with asyncio.timeout(remaining):
                    header = await reader.readexactly(80)
                    payload = await reader.readexactly(header[79])
                if self._writer is not writer:
                    return
                if int.from_bytes(header[2:4], "big") != MARKER_RX:
                    continue
                try:
                    frame = parse_local_frame(payload)
                except ValueError as err:
                    if payload.startswith(b"\xff\xff"):
                        self._history.record(self._mac, payload, None, str(err))
                    _LOGGER.debug("Ignoring Haier local frame from %s: %s", self._ip, err)
                    continue
                self._history.record(self._mac, payload, frame)
                sub = frame[10:12]
                if frame[9] == 0x04 and sub == b"\x0f\x5a":
                    try:
                        self._alarm_bits = decode_alarm_bits(frame)
                    except ValueError:
                        continue
                    self._notify()
                    continue
                if frame[9] not in (0x02, 0x06):
                    continue
                if sub == _BIG_SUB:
                    self._big_frame = frame
                    self._big_frame_at = monotonic()
                elif sub == _STATUS_SUB:
                    self._frame = frame
                    self._frame_at = monotonic()
                    status_deadline = self._frame_at + FRAME_TIMEOUT
                else:
                    continue
                self._notify()
        except (asyncio.IncompleteReadError, OSError, TimeoutError) as err:
            if not self._stopped:
                _LOGGER.debug("Haier local connection to %s lost: %s", self._ip, err)
        finally:
            self._disconnect(writer)

    async def _write(self, writer: asyncio.StreamWriter, payload: bytes) -> None:
        if self._writer is not writer:
            raise ConnectionError("Haier local connection closed")
        if writer.is_closing():
            self._disconnect(writer)
            raise ConnectionError("Haier local connection closed")
        try:
            writer.write(_envelope(payload, self._mac, self._next_seq))
            await writer.drain()
        except OSError:
            self._disconnect(writer)
            raise

    async def async_poll(self, _devid: str | None = None) -> None:
        writer = await self._connect()
        await self._write(writer, POLL_FRAME)
        await asyncio.sleep(0.25)
        await self._write(writer, BIG_POLL_FRAME)

    async def async_send_frame(self, _devid: str, frame: bytes) -> None:
        if self._writer is None:
            raise ConnectionError("Haier local connection closed")
        await self._write(self._writer, frame)

    async def async_stop(self) -> None:
        self._stopped = True
        tasks = [task for task in (self._read_task, self._keepalive_task) if task]
        for task in tasks:
            task.cancel()
        if self._writer is not None:
            self._disconnect(self._writer)
        await asyncio.gather(*tasks, return_exceptions=True)
