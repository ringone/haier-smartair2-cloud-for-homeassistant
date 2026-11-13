"""Diagnostic binary sensors from Haier status and alarm reports."""

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

_ACTUATORS = (
    ("compressor_on", "compressor", True),
    ("indoor_fan_on", "indoor_fan", True),
    ("defrost_on", "defrost", True),
    ("outdoor_fan", "outdoor_fan", False),
    ("four_way_valve", "four_way_valve", False),
    ("indoor_electric_heat_on", "indoor_electric_heater", False),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: HaierConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up diagnostic binary sensors."""
    entities = []
    for coord in entry.runtime_data.coordinators:
        if coord.codec.supports_extras:
            entities.append(
                HaierFlag(coord, "filter_change", "filter", BinarySensorDeviceClass.PROBLEM)
            )
            if not coord.via_cloud:
                entities.extend(
                    HaierFlag(coord, field, key, BinarySensorDeviceClass.RUNNING, enabled)
                    for field, key, enabled in _ACTUATORS
                )
                entities.append(HaierAlarms(coord))
    async_add_entities(entities)


class HaierFlag(CoordinatorEntity[HaierCoordinator], BinarySensorEntity):
    """A reported device flag with an optional state."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: HaierCoordinator,
        field: str,
        translation_key: str,
        device_class: BinarySensorDeviceClass,
        enabled: bool = True,
    ) -> None:
        super().__init__(coordinator)
        self._field = field
        self._attr_translation_key = translation_key
        self._attr_device_class = device_class
        self._attr_entity_registry_enabled_default = enabled
        self._attr_unique_id = f"{DOMAIN}_{coordinator.devid}_{field}"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, coordinator.devid)})

    @property
    def is_on(self) -> bool | None:
        return getattr(self.coordinator.data, self._field, None)


class HaierAlarms(HaierFlag):
    """Indicate whether the most recent alarm bitmap has any active bits."""

    def __init__(self, coordinator: HaierCoordinator) -> None:
        super().__init__(
            coordinator, "alarm_bits", "active_alarms", BinarySensorDeviceClass.PROBLEM
        )

    @property
    def is_on(self) -> bool | None:
        bits = getattr(self.coordinator.data, "alarm_bits", None)
        return bool(bits) if bits is not None else None

    @property
    def extra_state_attributes(self) -> dict[str, list[int]]:
        bits = getattr(self.coordinator.data, "alarm_bits", None)
        return {"active_alarm_bits": list(bits)} if bits is not None else {}
