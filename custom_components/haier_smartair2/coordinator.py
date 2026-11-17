"""Per-device update coordinator bridging a transport + codec to HA."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .codec import Codec, HaierState
from .const import SCAN_INTERVAL_SECONDS

_LOGGER = logging.getLogger(__name__)


class HaierCoordinator(DataUpdateCoordinator[HaierState]):
    """Keeps one device's state fresh via periodic poll + async push."""

    def __init__(
        self,
        hass: HomeAssistant,
        transport,
        codec: Codec,
        devid: str,
        name: str,
        via_cloud: bool,
        config_entry=None,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=f"Haier {name}",
            update_interval=timedelta(seconds=SCAN_INTERVAL_SECONDS),
        )
        self.transport = transport
        self.codec = codec
        self.devid = devid.upper()
        self.dev_name = name
        self.via_cloud = via_cloud
        self._last_fixed_swing: int | None = None
        transport.add_listener(self._on_push)

    def _decode_latest(self) -> HaierState | None:
        frame = self.transport.latest_frame(self.devid)
        if not frame:
            return None
        try:
            state = self.codec.decode(frame)
        except Exception:  # noqa: BLE001
            _LOGGER.debug("decode failed for %s", self.devid, exc_info=True)
            return None
        big_frame = None
        latest_big = getattr(self.transport, "latest_big_frame", None)
        if latest_big is not None:
            big_frame = latest_big(self.devid)
        if big_frame is not None:
            try:
                extra = self.codec.decode_big(big_frame)
            except Exception:  # noqa: BLE001
                _LOGGER.debug("big-data decode failed for %s", self.devid, exc_info=True)
                extra = {}
            if extra:
                state = state.merged(**extra)
        if not self.via_cloud:
            state = state.merged(alarm_bits=self.transport.latest_alarm_bits())
        if state.swing_pos not in (None, 0x0C, 0x0E):
            self._last_fixed_swing = state.swing_pos
        return state

    def _on_push(self) -> None:
        state = self._decode_latest()
        if state is not None:
            self.async_set_updated_data(state)
        elif not self.via_cloud and not self.transport.is_online(self.devid):
            self.async_set_update_error(UpdateFailed("Haier local connection closed"))

    async def _async_update_data(self) -> HaierState:
        try:
            await self.transport.async_poll(self.devid)
        except (OSError, TimeoutError) as err:
            if self.via_cloud:
                raise
            raise UpdateFailed("Haier local poll failed") from err
        for _ in range(10):
            await asyncio.sleep(0.2)
            state = self._decode_latest()
            if state is not None:
                return state
        if not self.via_cloud:
            raise UpdateFailed("No recent Haier local status frame")
        return self.data or HaierState()

    async def async_apply(self, **changes) -> None:
        """Send a control command (read-modify-write) and refresh."""
        if self.via_cloud:
            state = self.data or self._decode_latest() or HaierState()
        else:
            state = self._decode_latest()
            if state is None:
                raise UpdateFailed("No recent Haier local status frame")
        # While swinging, the status nibble is the auto code, so turning swing
        # off has to restore the last fixed vane position.
        if changes.get("swing_v") is False and self._last_fixed_swing is not None:
            state = state.merged(swing_pos=self._last_fixed_swing)
        frame = self.codec.encode_set(state, **changes)
        await self.transport.async_send_frame(self.devid, frame)
        await asyncio.sleep(0.6)
        await self.async_request_refresh()
