import logging
import os
import voluptuous as vol

from homeassistant.components.sensor import (
    SensorEntity,
    PLATFORM_SCHEMA,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    CONF_NAME,
    CONF_UNIQUE_ID,
    UnitOfElectricPotential,
    UnitOfElectricCurrent,
    UnitOfPower,
    UnitOfTime,
)
from homeassistant.helpers.entity import DeviceInfo
import homeassistant.helpers.config_validation as cv

from .ina219 import INA219
from .ups_hat_e import UPSHatEData
from .const import (
    MIN_CHARGING_CURRENT,
    MIN_ONLINE_CURRENT,
    MIN_BATTERY_CONNECTED_CURRENT,
    LOW_BATTERY_PERCENTAGE,
    DOMAIN,
    CONF_MODEL,
    MODEL_E,
)

_LOGGER = logging.getLogger(__name__)

ATTR_CAPACITY = "capacity"
ATTR_SOC = "soc"
ATTR_REAL_SOC = "real_soc"
ATTR_PSU_VOLTAGE = "psu_voltage"
ATTR_SHUNT_VOLTAGE = "shunt_voltage"
ATTR_LOAD_VOLTAGE = "load_voltage"
ATTR_CURRENT = "current"
ATTR_POWER = "power"
ATTR_CHARGING = "charging"
ATTR_ONLINE = "online"
ATTR_BATTERY_CONNECTED = "battery_connected"
ATTR_LOW_BATTERY = "low_battery"
ATTR_POWER_CALCULATED = "power_calculated"

ATTR_REMAINING_BATTERY_CAPACITY = "remaining_battery_capacity"
ATTR_REMAINING_TIME = "remaining_time_min"

CONF_BATTERY_CAPACITY = "battery_capacity"
CONF_MAX_SOC = 'max_soc'
DEFAULT_NAME = "waveshare_ups_hat"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_MODEL): cv.string,
    vol.Optional(CONF_MAX_SOC, default=100): cv.positive_int,
    vol.Optional(CONF_BATTERY_CAPACITY): cv.positive_int,
    vol.Optional(CONF_UNIQUE_ID): cv.string,
})


# Entity definitions for the UPS HAT (E). Each tuple drives one SensorEntity.
# key, friendly suffix, data key, unit, device_class, state_class, factor, round
E_SENSORS = (
    ("battery", "Battery", "battery_percent", PERCENTAGE,
     SensorDeviceClass.BATTERY, SensorStateClass.MEASUREMENT, 1, 0),
    ("battery_voltage", "Battery Voltage", "battery_voltage", UnitOfElectricPotential.VOLT,
     SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT, 0.001, 3),
    ("battery_current", "Battery Current", "battery_current", UnitOfElectricCurrent.AMPERE,
     SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT, 0.001, 3),
    ("vbus_voltage", "VBUS Voltage", "vbus_voltage", UnitOfElectricPotential.VOLT,
     SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT, 0.001, 3),
    ("vbus_current", "VBUS Current", "vbus_current", UnitOfElectricCurrent.AMPERE,
     SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT, 0.001, 3),
    ("vbus_power", "VBUS Power", "vbus_power", UnitOfPower.WATT,
     SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, 0.001, 3),
    ("remaining_capacity", "Remaining Capacity", "remaining_capacity", "mAh",
     None, SensorStateClass.MEASUREMENT, 1, 0),
    ("time_to_empty", "Time To Empty", "time_to_empty", UnitOfTime.MINUTES,
     SensorDeviceClass.DURATION, None, 1, 0),
    ("time_to_full", "Time To Full", "time_to_full", UnitOfTime.MINUTES,
     SensorDeviceClass.DURATION, None, 1, 0),
    ("status", "Status", "status", None, None, None, None, None),
    ("cell_voltage_1", "Cell Voltage 1", "cell_voltage_1", UnitOfElectricPotential.VOLT,
     SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT, 0.001, 3),
    ("cell_voltage_2", "Cell Voltage 2", "cell_voltage_2", UnitOfElectricPotential.VOLT,
     SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT, 0.001, 3),
    ("cell_voltage_3", "Cell Voltage 3", "cell_voltage_3", UnitOfElectricPotential.VOLT,
     SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT, 0.001, 3),
    ("cell_voltage_4", "Cell Voltage 4", "cell_voltage_4", UnitOfElectricPotential.VOLT,
     SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT, 0.001, 3),
)


def _device_info(base_id, name):
    return DeviceInfo(
        identifiers={(DOMAIN, base_id)},
        name=name,
        manufacturer="Waveshare",
        model="UPS HAT (E)",
    )


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Waveshare UPS Hat sensor."""
    name = config.get(CONF_NAME)
    model = config.get(CONF_MODEL)
    unique_id = config.get(CONF_UNIQUE_ID)

    if model == MODEL_E:
        base_id = unique_id or name
        data = UPSHatEData()
        entities = [
            WaveshareUpsHatESensor(data, name, base_id, desc) for desc in E_SENSORS
        ]
        add_entities(entities, True)
        return

    max_soc = config.get(CONF_MAX_SOC)
    battery_capacity = config.get(CONF_BATTERY_CAPACITY)
    add_entities([WaveshareUpsHat(name, unique_id, max_soc, battery_capacity)], True)


class WaveshareUpsHatESensor(SensorEntity):
    """A single sensor entity for the Waveshare UPS HAT (E)."""

    def __init__(self, data, name, base_id, desc):
        key, suffix, data_key, unit, device_class, state_class, factor, ndigits = desc
        self._data = data
        self._data_key = data_key
        self._factor = factor
        self._ndigits = ndigits
        self._attr_name = f"{name} {suffix}"
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_unique_id = f"{base_id}_{key}" if base_id else None
        self._attr_device_info = _device_info(base_id, name)

    def update(self):
        """Refresh shared data (throttled) and pull this entity's value."""
        self._data.update()
        value = self._data.data.get(self._data_key)
        if value is not None and self._factor is not None:
            value = value * self._factor
            if self._ndigits is not None:
                value = round(value, self._ndigits)
        self._attr_native_value = value


class WaveshareUpsHat(SensorEntity):
    """Representation of a Waveshare UPS Hat."""

    def __init__(self, name, unique_id=None, max_soc=None, battery_capacity=None):
        """Initialize the sensor."""
        self._name = name
        self._unique_id = unique_id
        if max_soc > 100:
            max_soc = 100
        elif max_soc < 1:
            max_soc = 1
        self._max_soc = max_soc
        self._battery_capacity = battery_capacity
        self._ina219 = INA219(addr=0x42)
        self._attrs = {}

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def device_class(self):
        """Return the device class of the sensor."""
        return SensorDeviceClass.BATTERY

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._attrs.get(ATTR_SOC)

    @property
    def unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        return PERCENTAGE

    @property
    def extra_state_attributes(self):
        """Return the state attributes of the sensor."""
        return self._attrs

    @property
    def unique_id(self):
        """Return the unique id of the sensor."""
        return self._unique_id

    def update(self):
        """Get the latest data and update the states."""
        ina219 = self._ina219
        bus_voltage = ina219.getBusVoltage_V()  # Voltage on V- (load side)
        shunt_voltage = (
            ina219.getShuntVoltage_mV() / 1000
        )  # Voltage between V+ and V- across the shunt
        current = ina219.getCurrent_mA()  # Current in mA
        power = ina219.getPower_W()  # Power in W

        real_soc = (bus_voltage - 6) / 2.4 * 100
        soc = (bus_voltage - 6) / (2.4 * (self._max_soc / 100.0)) * 100

        soc = min(max(soc, 0), 100)

        online = current > MIN_ONLINE_CURRENT
        charging = current > MIN_CHARGING_CURRENT
        low_battery = online and soc < LOW_BATTERY_PERCENTAGE
        power_calculated = bus_voltage * (current / 1000)

        if self._battery_capacity is None:
            remaining_battery_capacity = None
            remaining_time = None
        else:
            remaining_battery_capacity = (real_soc / 100.0) * self._battery_capacity
            if current < 0:
                remaining_time = round((remaining_battery_capacity / -current) * 60.0, 0)
            else:
                remaining_time = None

        self._attrs = {
            ATTR_CAPACITY: round(soc, 0),
            ATTR_SOC: round(soc, 0),
            ATTR_REAL_SOC: real_soc,
            ATTR_PSU_VOLTAGE: round(bus_voltage + shunt_voltage, 5),
            ATTR_LOAD_VOLTAGE: round(bus_voltage, 5),
            ATTR_SHUNT_VOLTAGE: round(shunt_voltage, 5),
            ATTR_CURRENT: round(current, 5),
            ATTR_POWER: round(power, 5),
            ATTR_POWER_CALCULATED: round(power_calculated, 5),
            ATTR_CHARGING: charging,
            ATTR_ONLINE: online,
            ATTR_REMAINING_BATTERY_CAPACITY: remaining_battery_capacity,
            ATTR_REMAINING_TIME: remaining_time,
            ATTR_LOW_BATTERY: low_battery
        }
