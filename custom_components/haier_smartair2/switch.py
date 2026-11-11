"""Switches for Haier SmartAir2 extra functions."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import HaierConfigEntry
from .const import DOMAIN
from .coordinator import HaierCoordinator

# state attribute, translation key, icon
_SWITCHES = (
    ("health", "health", "mdi:leaf"),
    ("display", "display", "mdi:led-on"),
    ("self_clean", "self_clean", "mdi:shimmer"),
    ("lock_remote", "lock_remote", "mdi:lock"),
    ("electric_heat", "electric_heat", "mdi:radiator"),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: HaierConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up switches for V3 devices."""
    entities: list[SwitchEntity] = []
    for coord in entry.runtime_data.coordinators:
        if not coord.codec.supports_extras:
            continue
        entities.extend(HaierSwitch(coord, key, translation, icon) for key, translation, icon in _SWITCHES)
    async_add_entities(entities)


class HaierSwitch(CoordinatorEntity[HaierCoordinator], SwitchEntity):
    """A boolean function of the air conditioner."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: HaierCoordinator, key: str, translation_key: str, icon: str) -> None:
        super().__init__(coordinator)
        self._key = key
        self._attr_translation_key = translation_key
        self._attr_icon = icon
        self._attr_unique_id = f"{DOMAIN}_{coordinator.devid}_{key}"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, coordinator.devid)})

    @property
    def is_on(self) -> bool | None:
        data = self.coordinator.data
        if data is None:
            return None
        value = getattr(data, self._key, None)
        if value is None:
            return None
        return bool(value)

    @property
    def available(self) -> bool:
        return super().available and self.is_on is not None

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.async_apply(**{self._key: True})

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.async_apply(**{self._key: False})
