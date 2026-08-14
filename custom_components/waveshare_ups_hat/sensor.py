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

from .const import CONF_MODEL, DOMAIN, LOW_BATTERY_PERCENTAGE, MODEL_E
from .coordinator import WaveshareUpsCoordinator

# Battery % below this while charging counts as an active recharge cycle.
RECHARGE_THRESHOLD = 95

SYSTEM_STATE_OPTIONS = ("ok", "recharging", "on_battery", "low_battery")


@dataclass(frozen=True, kw_only=True)
class WaveshareSensorEntityDescription(SensorEntityDescription):
    """Describes a Waveshare UPS sensor."""

    value_fn: Callable[[dict[str, Any]], Any]


def _system_state_e(data: dict[str, Any]) -> str:
    """High-level state for UPS HAT (E)."""
    percent = data.get("battery_percent")
    if percent is None:
        percent = 100
    discharging = bool(data.get("is_discharging")) or data.get("status") == "discharging"
    online = bool(data.get("online"))
    charging = bool(data.get("is_charging"))

    if discharging or not online:
        if percent < LOW_BATTERY_PERCENTAGE:
            return "low_battery"
        return "on_battery"
    if charging and percent < RECHARGE_THRESHOLD:
        return "recharging"
    return "ok"


def _system_state_classic(data: dict[str, Any]) -> str:
    """High-level state for classic INA219 HAT."""
    percent = data.get("soc")
    if percent is None:
        percent = 100
    online = bool(data.get("online"))
    charging = bool(data.get("charging"))

    if not online:
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


def _charge_current_ma(data: dict[str, Any]) -> float | None:
    """Positive current into the batteries (mA, classic). 0 when discharging."""
    raw = data.get("current")
    if raw is None:
        return None
    return round(raw, 1) if raw > 0 else 0.0


def _discharge_current_ma(data: dict[str, Any]) -> float | None:
    """Positive current out of the batteries (mA, classic). 0 when charging."""
    raw = data.get("current")
    if raw is None:
        return None
    return round(-raw, 1) if raw < 0 else 0.0


E_SENSORS: tuple[WaveshareSensorEntityDescription, ...] = (
    WaveshareSensorEntityDescription(
        key="system_state",
        name="System state",
        translation_key="system_state",
        device_class=SensorDeviceClass.ENUM,
        options=list(SYSTEM_STATE_OPTIONS),
        value_fn=_system_state_e,
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
        key="charging_status",
        name="Charging status",
        value_fn=lambda d: d.get("status"),
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

CLASSIC_SENSORS: tuple[WaveshareSensorEntityDescription, ...] = (
    WaveshareSensorEntityDescription(
        key="system_state",
        name="System state",
        translation_key="system_state",
        device_class=SensorDeviceClass.ENUM,
        options=list(SYSTEM_STATE_OPTIONS),
        value_fn=_system_state_classic,
    ),
    WaveshareSensorEntityDescription(
        key="battery_percent",
        name="Battery",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.get("soc"),
    ),
    WaveshareSensorEntityDescription(
        key="psu_voltage",
        name="PSU voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        value_fn=lambda d: d.get("psu_voltage"),
    ),
    WaveshareSensorEntityDescription(
        key="load_voltage",
        name="Load voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        value_fn=lambda d: d.get("load_voltage"),
    ),
    WaveshareSensorEntityDescription(
        key="shunt_voltage",
        name="Shunt voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=5,
        value_fn=lambda d: d.get("shunt_voltage"),
    ),
    WaveshareSensorEntityDescription(
        key="battery_charge_current",
        name="Battery charge current",
        native_unit_of_measurement=UnitOfElectricCurrent.MILLIAMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=_charge_current_ma,
    ),
    WaveshareSensorEntityDescription(
        key="battery_discharge_current",
        name="Battery discharge current",
        native_unit_of_measurement=UnitOfElectricCurrent.MILLIAMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=_discharge_current_ma,
    ),
    WaveshareSensorEntityDescription(
        key="power",
        name="Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        value_fn=lambda d: d.get("power"),
    ),
    WaveshareSensorEntityDescription(
        key="remaining_capacity",
        name="Remaining capacity",
        native_unit_of_measurement="mAh",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.get("remaining_battery_capacity"),
    ),
    WaveshareSensorEntityDescription(
        key="runtime_remaining",
        name="Runtime remaining",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        device_class=SensorDeviceClass.DURATION,
        value_fn=lambda d: d.get("remaining_time_min"),
    ),
)


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
        # Force semantic entity IDs (e.g. sensor.shop_ups_battery_3_voltage)
        # instead of device-class based ones (sensor.shop_ups_voltage_5).
        self._attr_suggested_object_id = description.key
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
