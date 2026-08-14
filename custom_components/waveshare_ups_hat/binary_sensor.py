"""Binary sensor platform for Waveshare UPS Hat."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_MODEL, DOMAIN, MODEL_E
from .coordinator import WaveshareUpsCoordinator


@dataclass(frozen=True, kw_only=True)
class WaveshareBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes a Waveshare UPS binary sensor."""

    value_fn: Callable[[dict[str, Any]], bool]


E_BINARY_SENSORS: tuple[WaveshareBinarySensorEntityDescription, ...] = (
    WaveshareBinarySensorEntityDescription(
        key="ac_power",
        translation_key="ac_power",
        device_class=BinarySensorDeviceClass.POWER,
        value_fn=lambda d: bool(d.get("online")),
    ),
    WaveshareBinarySensorEntityDescription(
        key="charging",
        translation_key="charging",
        device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
        value_fn=lambda d: bool(d.get("is_charging")),
    ),
)

CLASSIC_BINARY_SENSORS: tuple[WaveshareBinarySensorEntityDescription, ...] = (
    WaveshareBinarySensorEntityDescription(
        key="ac_power",
        translation_key="ac_power",
        device_class=BinarySensorDeviceClass.POWER,
        value_fn=lambda d: bool(d.get("online")),
    ),
    WaveshareBinarySensorEntityDescription(
        key="charging",
        translation_key="charging",
        device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
        value_fn=lambda d: bool(d.get("charging")),
    ),
    WaveshareBinarySensorEntityDescription(
        key="low_battery",
        translation_key="low_battery",
        device_class=BinarySensorDeviceClass.BATTERY,
        value_fn=lambda d: bool(d.get("low_battery")),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensors from a config entry."""
    coordinator: WaveshareUpsCoordinator = hass.data[DOMAIN][entry.entry_id]
    model = entry.data[CONF_MODEL]

    descriptions = (
        E_BINARY_SENSORS if model == MODEL_E else CLASSIC_BINARY_SENSORS
    )
    async_add_entities(
        WaveshareUpsBinarySensor(coordinator, entry, description)
        for description in descriptions
    )


class WaveshareUpsBinarySensor(
    CoordinatorEntity[WaveshareUpsCoordinator], BinarySensorEntity
):
    """A binary sensor for the Waveshare UPS Hat."""

    entity_description: WaveshareBinarySensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: WaveshareUpsCoordinator,
        entry: ConfigEntry,
        description: WaveshareBinarySensorEntityDescription,
    ) -> None:
        """Initialize the binary sensor."""
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
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)
