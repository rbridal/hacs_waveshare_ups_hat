import voluptuous as vol
from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
    PLATFORM_SCHEMA,
)
from homeassistant.const import CONF_NAME, CONF_UNIQUE_ID
from homeassistant.helpers.entity import DeviceInfo
import homeassistant.helpers.config_validation as cv

from .ina219 import INA219
from .ups_hat_e import UPSHatEData
from .const import MIN_ONLINE_CURRENT, DOMAIN, CONF_MODEL, MODEL_E

DEFAULT_NAME = "waveshare_ups_hat_online"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_MODEL): cv.string,
    vol.Optional(CONF_UNIQUE_ID): cv.string,
})

# key, friendly suffix, data key, device_class
E_BINARY_SENSORS = (
    ("online", "Online", "online", BinarySensorDeviceClass.POWER),
    ("charging", "Charging", "is_charging", BinarySensorDeviceClass.BATTERY_CHARGING),
)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up an Online Status binary sensor."""
    model = config.get(CONF_MODEL)

    if model == MODEL_E:
        name = config.get(CONF_NAME)
        if name == DEFAULT_NAME:
            name = "UPS"
        base_id = config.get(CONF_UNIQUE_ID) or name
        data = UPSHatEData()
        add_entities(
            [WaveshareUpsHatEBinarySensor(data, name, base_id, desc) for desc in E_BINARY_SENSORS],
            True,
        )
        return

    add_entities([OnlineStatus(config, {})], True)


class WaveshareUpsHatEBinarySensor(BinarySensorEntity):
    """A binary sensor for the Waveshare UPS HAT (E)."""

    def __init__(self, data, name, base_id, desc):
        key, suffix, data_key, device_class = desc
        self._data = data
        self._data_key = data_key
        self._attr_name = f"{name} {suffix}"
        self._attr_device_class = device_class
        self._attr_unique_id = f"{base_id}_{key}" if base_id else None
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, base_id)},
            name=name,
            manufacturer="Waveshare",
            model="UPS HAT (E)",
        )

    def update(self):
        self._data.update()
        self._attr_is_on = bool(self._data.data.get(self._data_key))


class OnlineStatus(BinarySensorEntity):
    """Representation of an UPS online status."""

    def __init__(self, config, data):
        """Initialize the UPS online status binary device."""
        self._name = DEFAULT_NAME
        self._ina219 = INA219(addr=0x42)
        self._state = True

    @property
    def name(self):
        """Return the name of the UPS online status sensor."""
        return self._name

    @property
    def device_class(self):
        """Return the device class of the binary sensor."""
        return BinarySensorDeviceClass.POWER

    @property
    def is_on(self):
        """Return true if the UPS is online, else false."""
        return self._state

    def update(self):
        """Get the status from UPS online status and set this entity's state."""
        self._state = self._ina219.getCurrent_mA() > MIN_ONLINE_CURRENT
