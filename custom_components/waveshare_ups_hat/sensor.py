"""Sensor platform for Waveshare UPS Hat."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfPower,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_MODEL, DOMAIN, MODEL_E
from .coordinator import WaveshareUpsCoordinator


@dataclass(frozen=True, kw_only=True)
class WaveshareSensorEntityDescription(SensorEntityDescription):
    """Describes a Waveshare UPS sensor."""

    value_fn: Callable[[dict[str, Any]], Any]


E_SENSORS: tuple[WaveshareSensorEntityDescription, ...] = (
    WaveshareSensorEntityDescription(
        key="battery",
        translation_key="battery",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.get("battery_percent"),
    ),
    WaveshareSensorEntityDescription(
        key="battery_voltage",
        translation_key="battery_voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        value_fn=lambda d: _scale(d.get("battery_voltage"), 0.001),
    ),
    WaveshareSensorEntityDescription(
        key="battery_current",
        translation_key="battery_current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        value_fn=lambda d: _scale(d.get("battery_current"), 0.001),
    ),
    WaveshareSensorEntityDescription(
        key="vbus_voltage",
        translation_key="vbus_voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        value_fn=lambda d: _scale(d.get("vbus_voltage"), 0.001),
    ),
    WaveshareSensorEntityDescription(
        key="vbus_current",
        translation_key="vbus_current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        value_fn=lambda d: _scale(d.get("vbus_current"), 0.001),
    ),
    WaveshareSensorEntityDescription(
        key="vbus_power",
        translation_key="vbus_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        value_fn=lambda d: _scale(d.get("vbus_power"), 0.001),
    ),
    WaveshareSensorEntityDescription(
        key="remaining_capacity",
        translation_key="remaining_capacity",
        native_unit_of_measurement="mAh",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.get("remaining_capacity"),
    ),
    WaveshareSensorEntityDescription(
        key="time_to_empty",
        translation_key="time_to_empty",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        device_class=SensorDeviceClass.DURATION,
        value_fn=lambda d: d.get("time_to_empty"),
    ),
    WaveshareSensorEntityDescription(
        key="time_to_full",
        translation_key="time_to_full",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        device_class=SensorDeviceClass.DURATION,
        value_fn=lambda d: d.get("time_to_full"),
    ),
    WaveshareSensorEntityDescription(
        key="status",
        translation_key="status",
        value_fn=lambda d: d.get("status"),
    ),
    WaveshareSensorEntityDescription(
        key="cell_voltage_1",
        translation_key="cell_voltage_1",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        value_fn=lambda d: _scale(d.get("cell_voltage_1"), 0.001),
    ),
    WaveshareSensorEntityDescription(
        key="cell_voltage_2",
        translation_key="cell_voltage_2",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        value_fn=lambda d: _scale(d.get("cell_voltage_2"), 0.001),
    ),
    WaveshareSensorEntityDescription(
        key="cell_voltage_3",
        translation_key="cell_voltage_3",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        value_fn=lambda d: _scale(d.get("cell_voltage_3"), 0.001),
    ),
    WaveshareSensorEntityDescription(
        key="cell_voltage_4",
        translation_key="cell_voltage_4",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        value_fn=lambda d: _scale(d.get("cell_voltage_4"), 0.001),
    ),
)

CLASSIC_SENSORS: tuple[WaveshareSensorEntityDescription, ...] = (
    WaveshareSensorEntityDescription(
        key="soc",
        translation_key="battery",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.get("soc"),
    ),
    WaveshareSensorEntityDescription(
        key="psu_voltage",
        translation_key="psu_voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        value_fn=lambda d: d.get("psu_voltage"),
    ),
    WaveshareSensorEntityDescription(
        key="load_voltage",
        translation_key="load_voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        value_fn=lambda d: d.get("load_voltage"),
    ),
    WaveshareSensorEntityDescription(
        key="shunt_voltage",
        translation_key="shunt_voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=5,
        value_fn=lambda d: d.get("shunt_voltage"),
    ),
    WaveshareSensorEntityDescription(
        key="current",
        translation_key="current",
        native_unit_of_measurement=UnitOfElectricCurrent.MILLIAMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda d: d.get("current"),
    ),
    WaveshareSensorEntityDescription(
        key="power",
        translation_key="power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        value_fn=lambda d: d.get("power"),
    ),
    WaveshareSensorEntityDescription(
        key="remaining_battery_capacity",
        translation_key="remaining_capacity",
        native_unit_of_measurement="mAh",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.get("remaining_battery_capacity"),
    ),
    WaveshareSensorEntityDescription(
        key="remaining_time_min",
        translation_key="time_to_empty",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        device_class=SensorDeviceClass.DURATION,
        value_fn=lambda d: d.get("remaining_time_min"),
    ),
)


def _scale(value: Any, factor: float) -> float | None:
    if value is None:
        return None
    return round(value * factor, 3)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors from a config entry."""
    coordinator: WaveshareUpsCoordinator = hass.data[DOMAIN][entry.entry_id]
    model = entry.data[CONF_MODEL]

    descriptions = E_SENSORS if model == MODEL_E else CLASSIC_SENSORS
    async_add_entities(
        WaveshareUpsSensor(coordinator, entry, description)
        for description in descriptions
    )


class WaveshareUpsSensor(
    CoordinatorEntity[WaveshareUpsCoordinator], SensorEntity
):
    """A sensor for the Waveshare UPS Hat."""

    entity_description: WaveshareSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: WaveshareUpsCoordinator,
        entry: ConfigEntry,
        description: WaveshareSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.unique_id}_{description.key}"
        model_label = (
            "UPS HAT (E)" if entry.data[CONF_MODEL] == MODEL_E else "UPS HAT"
        )
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Waveshare",
            model=model_label,
        )

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)
