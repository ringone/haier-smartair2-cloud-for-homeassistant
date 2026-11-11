"""Diagnostic binary sensors from the Haier status frame."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import HaierConfigEntry
from .const import DOMAIN
from .coordinator import HaierCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: HaierConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up diagnostic binary sensors."""
    async_add_entities(
        HaierFilter(coord)
        for coord in entry.runtime_data.coordinators
        if coord.codec.supports_extras
    )


class HaierFilter(CoordinatorEntity[HaierCoordinator], BinarySensorEntity):
    """Filter replacement flag from the status frame."""

    _attr_has_entity_name = True
    _attr_translation_key = "filter"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: HaierCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_{coordinator.devid}_filter_change"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, coordinator.devid)})

    @property
    def is_on(self) -> bool | None:
        data = self.coordinator.data
        if data is None or data.filter_change is None:
            return None
        return bool(data.filter_change)
