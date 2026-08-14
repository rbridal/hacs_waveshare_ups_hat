"""Data update coordinator for Waveshare UPS Hat."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_ADDR,
    CONF_BATTERY_CAPACITY,
    CONF_BUS,
    CONF_MAX_SOC,
    CONF_MODEL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    LOW_BATTERY_PERCENTAGE,
    MIN_CHARGING_CURRENT,
    MIN_ONLINE_CURRENT,
    MODEL_E,
)
from .ina219 import INA219
from .ups_hat_e import UPSHatE

_LOGGER = logging.getLogger(__name__)


class WaveshareUpsCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator that polls the UPS over I2C."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
            config_entry=entry,
        )
        self.entry = entry
        self.model = entry.data[CONF_MODEL]
        self.bus = entry.data.get(CONF_BUS, 1)
        self.addr = entry.data[CONF_ADDR]
        self.max_soc = entry.data.get(CONF_MAX_SOC, 100)
        self.battery_capacity = entry.data.get(CONF_BATTERY_CAPACITY)

        self._ina219: INA219 | None = None
        self._ups_e: UPSHatE | None = None

        if self.model == MODEL_E:
            self._ups_e = UPSHatE(i2c_bus=self.bus, addr=self.addr)
        else:
            self._ina219 = INA219(i2c_bus=self.bus, addr=self.addr)

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from the UPS (runs I2C in executor)."""
        try:
            if self.model == MODEL_E:
                return await self.hass.async_add_executor_job(self._read_e)
            return await self.hass.async_add_executor_job(self._read_classic)
        except OSError as err:
            raise UpdateFailed(f"I2C read failed at 0x{self.addr:02x}: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Unexpected error reading UPS: {err}") from err

    def _read_e(self) -> dict[str, Any]:
        """Blocking read for UPS HAT (E)."""
        assert self._ups_e is not None
        return self._ups_e.read()

    def _read_classic(self) -> dict[str, Any]:
        """Blocking read for classic INA219-based HAT."""
        assert self._ina219 is not None
        ina = self._ina219

        bus_voltage = ina.getBusVoltage_V()
        shunt_voltage = ina.getShuntVoltage_mV() / 1000
        current = ina.getCurrent_mA()
        power = ina.getPower_W()

        real_soc = (bus_voltage - 6) / 2.4 * 100
        soc = (bus_voltage - 6) / (2.4 * (self.max_soc / 100.0)) * 100
        soc = min(max(soc, 0), 100)

        online = current > MIN_ONLINE_CURRENT
        charging = current > MIN_CHARGING_CURRENT
        low_battery = online and soc < LOW_BATTERY_PERCENTAGE
        power_calculated = bus_voltage * (current / 1000)

        remaining_battery_capacity = None
        remaining_time = None
        if self.battery_capacity is not None:
            remaining_battery_capacity = (real_soc / 100.0) * self.battery_capacity
            if current < 0:
                remaining_time = round(
                    (remaining_battery_capacity / -current) * 60.0, 0
                )

        return {
            "soc": round(soc, 0),
            "real_soc": real_soc,
            "psu_voltage": round(bus_voltage + shunt_voltage, 5),
            "load_voltage": round(bus_voltage, 5),
            "shunt_voltage": round(shunt_voltage, 5),
            "current": round(current, 5),
            "power": round(power, 5),
            "power_calculated": round(power_calculated, 5),
            "charging": charging,
            "online": online,
            "low_battery": low_battery,
            "remaining_battery_capacity": remaining_battery_capacity,
            "remaining_time_min": remaining_time,
        }
