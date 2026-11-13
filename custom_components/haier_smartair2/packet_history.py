"""Bounded on-disk history for incoming local EPP frames."""

from __future__ import annotations

import logging
from collections import OrderedDict, deque
from datetime import UTC, datetime
from time import time
from typing import Any, TypedDict

from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.storage import Store

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
RETENTION_SECONDS = 7 * 24 * 60 * 60
MAX_RECORDS = 20_000
SAMPLE_INTERVAL = 5 * 60
_SAVE_DELAY = 120
_MAX_STREAMS = 1_024

# Limit shared payloads to observed telemetry layouts, which have no device identifiers.
_SHAREABLE_LAYOUTS = {
    (0x02, "6d01", 24),
    (0x06, "6d01", 24),
    (0x02, "6d01", 32),
    (0x06, "6d01", 32),
    (0x02, "7d01", 46),
    (0x06, "7d01", 46),
    (0x04, "0f5a", 8),
}


class PacketRecord(TypedDict):
    """One incoming EPP payload, with metadata from validation."""

    timestamp: float
    device: str
    frame_type: int | None
    subcommand: str | None
    payload_hex: str
    validation_error: str | None
    shareable: bool


def history_store(hass: HomeAssistant, entry_id: str) -> Store[list[PacketRecord]]:
    """Open the local history for one config entry."""
    return Store(
        hass,
        1,
        f"{DOMAIN}.{entry_id}.packets",
        private=True,
        atomic_writes=True,
    )


class PacketHistory:
    """Save changes and periodic samples without blocking packet handling."""

    def __init__(self, store: Store[list[PacketRecord]]) -> None:
        self._store = store
        self._records: deque[PacketRecord] = deque(maxlen=MAX_RECORDS)
        self._latest: OrderedDict[
            tuple[str, int | None, str | None, bool], PacketRecord
        ] = OrderedDict()
        self._save_pending = False

    async def async_load(self) -> None:
        """Restore recent frames from disk."""
        try:
            records = await self._store.async_load() or []
        except (HomeAssistantError, OSError):
            _LOGGER.warning("Unable to load Haier packet history", exc_info=True)
            return
        self._records.extend(sorted(records, key=lambda record: record["timestamp"]))
        if self._prune(time()) or len(records) > MAX_RECORDS:
            self._schedule_save()

    def _prune(self, now: float) -> bool:
        cutoff = now - RETENTION_SECONDS
        kept = [record for record in self._records if record["timestamp"] >= cutoff]
        if len(kept) == len(self._records):
            return False
        self._records = deque(kept, maxlen=MAX_RECORDS)
        return True

    @callback
    def record(
        self,
        device: str,
        payload: bytes,
        frame: bytes | None,
        error: str | None = None,
    ) -> None:
        """Keep the original bytes before decoding or filtering message types."""
        now = time()
        # Invalid payloads are kept verbatim for local analysis only.
        frame_type = frame[9] if frame is not None else None
        subcommand = frame[10:12].hex() if frame is not None else None
        key = (device, frame_type, subcommand, error is not None)
        payload_hex = payload.hex()
        previous = self._latest.get(key)
        if (
            frame_type != 0x04
            and previous is not None
            and previous["payload_hex"] == payload_hex
            and previous["validation_error"] == error
            and 0 <= now - previous["timestamp"] < SAMPLE_INTERVAL
        ):
            return

        shareable = (
            frame is not None
            and frame[3] in (0, 0x40)
            and not any(frame[4:9])
            and (frame_type, subcommand, frame[2] - 10) in _SHAREABLE_LAYOUTS
        )
        record = PacketRecord(
            timestamp=now,
            device=device,
            frame_type=frame_type,
            subcommand=subcommand,
            payload_hex=payload_hex,
            validation_error=error,
            shareable=shareable,
        )
        self._records.append(record)
        self._latest[key] = record
        self._latest.move_to_end(key)
        if len(self._latest) > _MAX_STREAMS:
            self._latest.popitem(last=False)
        self._schedule_save()

    def _schedule_save(self) -> None:
        if not self._save_pending:
            self._save_pending = True
            self._store.async_delay_save(self._snapshot, _SAVE_DELAY)

    def _snapshot(self) -> list[PacketRecord]:
        self._save_pending = False
        now = time()
        self._prune(now)
        while self._latest:
            first = next(iter(self._latest.values()))
            if now - first["timestamp"] < SAMPLE_INTERVAL:
                break
            self._latest.popitem(last=False)
        return list(self._records)

    async def async_flush(self) -> None:
        """Save pending frames during integration unload."""
        expired = self._prune(time())
        if expired or self._save_pending:
            try:
                await self._store.async_save(self._snapshot())
            except (HomeAssistantError, OSError):
                _LOGGER.warning("Unable to save Haier packet history", exc_info=True)

    @callback
    def diagnostics(self, device: str | None = None) -> list[dict[str, Any]]:
        """Export recent records with anonymous devices and known telemetry."""
        if self._prune(time()):
            self._schedule_save()
        aliases: dict[str, int] = {}
        result = []
        for record in self._records:
            if device is not None and record["device"] != device:
                continue
            alias = aliases.setdefault(record["device"], len(aliases) + 1)
            result.append(
                {
                    "received_at": datetime.fromtimestamp(record["timestamp"], UTC).isoformat(),
                    "device": alias,
                    "frame_type": record["frame_type"],
                    "subcommand": record["subcommand"],
                    "length": len(record["payload_hex"]) // 2,
                    "validation_error": record["validation_error"],
                    "epp_hex": record["payload_hex"] if record["shareable"] else None,
                }
            )
        return result
