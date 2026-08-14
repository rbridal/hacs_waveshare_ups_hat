"""Data update coordinator for Waveshare UPS HAT (E)."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_ADDR, CONF_BUS, DEFAULT_SCAN_INTERVAL, DOMAIN
from .ups_hat_e import UPSHatE

_LOGGER = logging.getLogger(__name__)


class WaveshareUpsCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator that polls the UPS HAT (E) over I2C."""

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
        self.bus = entry.data.get(CONF_BUS, 1)
        self.addr = entry.data[CONF_ADDR]
        self._ups = UPSHatE(i2c_bus=self.bus, addr=self.addr)

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from the UPS (runs I2C in executor)."""
        try:
            return await self.hass.async_add_executor_job(self._ups.read)
        except OSError as err:
            raise UpdateFailed(f"I2C read failed at 0x{self.addr:02x}: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Unexpected error reading UPS: {err}") from err
