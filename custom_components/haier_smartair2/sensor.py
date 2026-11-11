"""Sensors for Haier SmartAir2."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import HaierConfigEntry
from .const import DOMAIN
from .coordinator import HaierCoordinator

# key, translation_key, device_class, unit, diagnostic, state_class, options
_EXTRA: tuple[tuple, ...] = (
    ("outdoor_temp", "outdoor_temperature", SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS, False, SensorStateClass.MEASUREMENT, None),
    ("humidity", "humidity", SensorDeviceClass.HUMIDITY, PERCENTAGE, False, SensorStateClass.MEASUREMENT, None),
    ("indoor_coil_temp", "indoor_coil_temperature", SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS, True, SensorStateClass.MEASUREMENT, None),
    ("outdoor_coil_temp", "outdoor_coil_temperature", SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS, True, SensorStateClass.MEASUREMENT, None),
    ("outdoor_in_temp", "outdoor_in_temperature", SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS, True, SensorStateClass.MEASUREMENT, None),
    ("outdoor_out_temp", "outdoor_out_temperature", SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS, True, SensorStateClass.MEASUREMENT, None),
    ("defrost_temp", "defrost_temperature", SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS, True, SensorStateClass.MEASUREMENT, None),
    ("compressor_hz", "compressor_frequency", SensorDeviceClass.FREQUENCY, UnitOfFrequency.HERTZ, True, SensorStateClass.MEASUREMENT, None),
    ("compressor_current", "compressor_current", SensorDeviceClass.CURRENT, UnitOfElectricCurrent.AMPERE, True, SensorStateClass.MEASUREMENT, None),
    ("power_w", "power", SensorDeviceClass.POWER, UnitOfPower.WATT, True, SensorStateClass.MEASUREMENT, None),
    ("expansion_valve", "expansion_valve", None, None, True, None, None),
    ("error_code", "error_code", None, None, True, None, None),
    ("operation_source", "operation_source", SensorDeviceClass.ENUM, None, True, None, ["other", "remote", "panel", "wifi"]),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: HaierConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up sensors."""
    entities: list[SensorEntity] = []
    for coord in entry.runtime_data.coordinators:
        entities.append(HaierRoomTemp(coord))
        if coord.codec.supports_extras:
            entities.extend(HaierValueSensor(coord, *spec) for spec in _EXTRA)
    async_add_entities(entities)


class _HaierSensor(CoordinatorEntity[HaierCoordinator], SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: HaierCoordinator, key: str, translation_key: str) -> None:
        super().__init__(coordinator)
        self._key = key
        self._attr_translation_key = translation_key
        self._attr_unique_id = f"{DOMAIN}_{coordinator.devid}_{key}"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, coordinator.devid)})

    @property
    def native_value(self):
        data = self.coordinator.data
        if data is None:
            return None
        return getattr(data, self._key, None)

    @property
    def available(self) -> bool:
        return super().available and self.native_value is not None


class HaierRoomTemp(_HaierSensor):
    """Room temperature reported by the AC."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    def __init__(self, coordinator: HaierCoordinator) -> None:
        super().__init__(coordinator, "current_temp", "room_temperature")


class HaierValueSensor(_HaierSensor):
    """One decoded value from the status or extended frame."""

    def __init__(
        self,
        coordinator: HaierCoordinator,
        key: str,
        translation_key: str,
        device_class,
        unit,
        diagnostic: bool,
        state_class,
        options,
    ) -> None:
        super().__init__(coordinator, key, translation_key)
        self._attr_device_class = device_class
        self._attr_native_unit_of_measurement = unit
        self._attr_state_class = state_class
        if diagnostic:
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
        if options:
            self._attr_options = options
