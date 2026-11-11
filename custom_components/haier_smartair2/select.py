"""Vertical louvre position for Haier SmartAir2."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import HaierConfigEntry
from .const import DOMAIN
from .coordinator import HaierCoordinator

# Option key -> protocol nibble. "auto" is swing mode 0x0C.
_POSITIONS = {
    "auto": None,
    "health_up": 0x01,
    "max_up": 0x02,
    "health_down": 0x03,
    "up": 0x04,
    "center": 0x06,
    "down": 0x08,
    "max_down": 0x0A,
}
_FROM_NIBBLE = {value: key for key, value in _POSITIONS.items() if value is not None}
_FROM_NIBBLE[0x0C] = "auto"
_FROM_NIBBLE[0x0E] = "auto"


async def async_setup_entry(
    hass: HomeAssistant, entry: HaierConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the vertical swing select."""
    async_add_entities(
        HaierSwingSelect(coord)
        for coord in entry.runtime_data.coordinators
        if coord.codec.supports_extras
    )


class HaierSwingSelect(CoordinatorEntity[HaierCoordinator], SelectEntity):
    """Vertical airflow position."""

    _attr_has_entity_name = True
    _attr_translation_key = "vertical_swing"
    _attr_options = list(_POSITIONS)
    _attr_icon = "mdi:swap-vertical"

    def __init__(self, coordinator: HaierCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_{coordinator.devid}_vertical_swing"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, coordinator.devid)})

    @property
    def current_option(self) -> str | None:
        data = self.coordinator.data
        if data is None or data.swing_pos is None:
            return None
        return _FROM_NIBBLE.get(data.swing_pos)

    async def async_select_option(self, option: str) -> None:
        nibble = _POSITIONS.get(option)
        if nibble is None:
            await self.coordinator.async_apply(swing_v=True)
        else:
            await self.coordinator.async_apply(swing_pos=nibble)
