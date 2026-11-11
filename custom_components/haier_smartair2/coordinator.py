"""Per-device update coordinator bridging a transport + codec to HA."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

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
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"Haier {name}",
            update_interval=timedelta(seconds=SCAN_INTERVAL_SECONDS),
        )
        self.transport = transport
        self.codec = codec
        self.devid = devid.upper()
        self.dev_name = name
        self.via_cloud = via_cloud
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
        return state

    def _on_push(self) -> None:
        state = self._decode_latest()
        if state is not None:
            self.async_set_updated_data(state)

    async def _async_update_data(self) -> HaierState:
        await self.transport.async_poll(self.devid)
        for _ in range(10):
            await asyncio.sleep(0.2)
            state = self._decode_latest()
            if state is not None:
                return state
        return self.data or HaierState()

    async def async_apply(self, **changes) -> None:
        """Send a control command (read-modify-write) and refresh."""
        state = self.data or self._decode_latest() or HaierState()
        frame = self.codec.encode_set(state, **changes)
        await self.transport.async_send_frame(self.devid, frame)
        await asyncio.sleep(0.6)
        await self.async_request_refresh()
