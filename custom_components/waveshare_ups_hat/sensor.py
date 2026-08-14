"""Sensor platform for Waveshare UPS HAT (E)."""
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

from .const import DOMAIN, LOW_BATTERY_PERCENTAGE
from .coordinator import WaveshareUpsCoordinator

# Battery % below this while charging counts as an active recharge cycle.
RECHARGE_THRESHOLD = 95

# VBUS (mV) above this means an AC adapter is present.
AC_PRESENT_MV = 1000

# Battery current (mA) below this (more negative) counts as discharging.
DISCHARGE_CURRENT_MA = -10

SYSTEM_STATE_OPTIONS = ("ok", "recharging", "on_battery", "low_battery")


@dataclass(frozen=True, kw_only=True)
class WaveshareSensorEntityDescription(SensorEntityDescription):
    """Describes a Waveshare UPS sensor."""

    value_fn: Callable[[dict[str, Any]], Any]


def _system_state(data: dict[str, Any]) -> str:
    """High-level state for UPS HAT (E).

    AC presence is based on VBUS voltage (not the MCU status flag), because the
    MCU can report "idle" while running on battery with the adapter unplugged.
    """
    percent = data.get("battery_percent")
    if percent is None:
        percent = 100

    vbus_mv = data.get("vbus_voltage") or 0
    battery_ma = data.get("battery_current") or 0
    charging = bool(data.get("is_charging"))

    ac_present = vbus_mv >= AC_PRESENT_MV
    discharging = battery_ma <= DISCHARGE_CURRENT_MA

    if not ac_present or discharging:
        if percent < LOW_BATTERY_PERCENTAGE:
            return "low_battery"
        return "on_battery"
    if charging and percent < RECHARGE_THRESHOLD:
        return "recharging"
    return "ok"


def _scale(value: Any, factor: float) -> float | None:
    if value is None:
        return None
    return round(value * factor, 3)


def _charge_current_a(data: dict[str, Any]) -> float | None:
    """Positive current into the batteries (A). 0 when discharging."""
    raw = data.get("battery_current")
    if raw is None:
        return None
    amps = raw * 0.001
    return round(amps, 3) if amps > 0 else 0.0


def _discharge_current_a(data: dict[str, Any]) -> float | None:
    """Positive current out of the batteries (A). 0 when charging."""
    raw = data.get("battery_current")
    if raw is None:
        return None
    amps = raw * 0.001
    return round(-amps, 3) if amps < 0 else 0.0


SENSORS: tuple[WaveshareSensorEntityDescription, ...] = (
    WaveshareSensorEntityDescription(
        key="system_state",
        name="System state",
        translation_key="system_state",
        device_class=SensorDeviceClass.ENUM,
        options=list(SYSTEM_STATE_OPTIONS),
        value_fn=_system_state,
    ),
    WaveshareSensorEntityDescription(
        key="battery_percent",
        name="Battery",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.get("battery_percent"),
    ),
    WaveshareSensorEntityDescription(
        key="battery_pack_voltage",
        name="Battery pack voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        value_fn=lambda d: _scale(d.get("battery_voltage"), 0.001),
    ),
    WaveshareSensorEntityDescription(
        key="battery_charge_current",
        name="Battery charge current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        value_fn=_charge_current_a,
    ),
    WaveshareSensorEntityDescription(
        key="battery_discharge_current",
        name="Battery discharge current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        value_fn=_discharge_current_a,
    ),
    WaveshareSensorEntityDescription(
        key="ac_adapter_voltage",
        name="AC adapter voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        value_fn=lambda d: _scale(d.get("vbus_voltage"), 0.001),
    ),
    WaveshareSensorEntityDescription(
        key="ac_adapter_current",
        name="AC adapter current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        value_fn=lambda d: _scale(d.get("vbus_current"), 0.001),
    ),
    WaveshareSensorEntityDescription(
        key="ac_adapter_power",
        name="AC adapter power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        value_fn=lambda d: _scale(d.get("vbus_power"), 0.001),
    ),
    WaveshareSensorEntityDescription(
        key="ac_adapter_input_status",
        name="AC adapter input status",
        value_fn=lambda d: d.get("status"),
    ),
    WaveshareSensorEntityDescription(
        key="remaining_capacity",
        name="Remaining capacity",
        native_unit_of_measurement="mAh",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.get("remaining_capacity"),
    ),
    WaveshareSensorEntityDescription(
        key="runtime_remaining",
        name="Runtime remaining",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        device_class=SensorDeviceClass.DURATION,
        value_fn=lambda d: d.get("time_to_empty"),
    ),
    WaveshareSensorEntityDescription(
        key="time_to_full_charge",
        name="Time to full charge",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        device_class=SensorDeviceClass.DURATION,
        value_fn=lambda d: d.get("time_to_full"),
    ),
    WaveshareSensorEntityDescription(
        key="battery_1_voltage",
        name="Battery 1 voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        value_fn=lambda d: _scale(d.get("cell_voltage_1"), 0.001),
    ),
    WaveshareSensorEntityDescription(
        key="battery_2_voltage",
        name="Battery 2 voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        value_fn=lambda d: _scale(d.get("cell_voltage_2"), 0.001),
    ),
    WaveshareSensorEntityDescription(
        key="battery_3_voltage",
        name="Battery 3 voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        value_fn=lambda d: _scale(d.get("cell_voltage_3"), 0.001),
    ),
    WaveshareSensorEntityDescription(
        key="battery_4_voltage",
        name="Battery 4 voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        value_fn=lambda d: _scale(d.get("cell_voltage_4"), 0.001),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors from a config entry."""
    coordinator: WaveshareUpsCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        WaveshareUpsSensor(coordinator, entry, description)
        for description in SENSORS
    )


class WaveshareUpsSensor(
    CoordinatorEntity[WaveshareUpsCoordinator], SensorEntity
):
    """A sensor for the Waveshare UPS HAT (E)."""

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
        self._attr_suggested_object_id = description.key
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Waveshare",
            model="UPS HAT (E)",
        )

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)
