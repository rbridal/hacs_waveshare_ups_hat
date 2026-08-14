"""Config flow for Waveshare UPS Hat."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    CONF_ADDR,
    CONF_BATTERY_CAPACITY,
    CONF_BUS,
    CONF_MAX_SOC,
    CONF_MODEL,
    DEFAULT_ADDR_CLASSIC,
    DEFAULT_ADDR_E,
    DEFAULT_BUS,
    DEFAULT_MAX_SOC,
    DEFAULT_NAME,
    DOMAIN,
    MODEL_CLASSIC,
    MODEL_E,
)


def _default_addr(model: str) -> int:
    return DEFAULT_ADDR_E if model == MODEL_E else DEFAULT_ADDR_CLASSIC


async def _async_validate_i2c(
    hass: HomeAssistant, model: str, bus: int, addr: int
) -> str | None:
    """Try a quick I2C read; return error key or None on success."""

    def _probe() -> None:
        if model == MODEL_E:
            from .ups_hat_e import UPSHatE

            UPSHatE(i2c_bus=bus, addr=addr).read()
        else:
            from .ina219 import INA219

            ina = INA219(i2c_bus=bus, addr=addr)
            ina.getBusVoltage_V()

    try:
        await hass.async_add_executor_job(_probe)
    except OSError:
        return "cannot_connect"
    except Exception:  # noqa: BLE001 - surface unexpected probe failures
        return "unknown"
    return None


class WaveshareUpsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Waveshare UPS Hat."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._model: str | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step: choose model."""
        if user_input is not None:
            self._model = user_input[CONF_MODEL]
            return await self.async_step_details()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_MODEL, default=MODEL_E): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                selector.SelectOptionDict(
                                    value=MODEL_E, label="UPS HAT (E)"
                                ),
                                selector.SelectOptionDict(
                                    value=MODEL_CLASSIC,
                                    label="Classic / UPS HAT (C) (INA219)",
                                ),
                            ],
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    ),
                }
            ),
        )

    async def async_step_details(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Collect name, bus, address, and classic-only options."""
        model = self._model or MODEL_E
        errors: dict[str, str] = {}

        if user_input is not None:
            name = user_input[CONF_NAME]
            bus = int(user_input[CONF_BUS])
            addr = int(user_input[CONF_ADDR], 0)  # accept 0x2d or 45

            await self.async_set_unique_id(f"{model}_{bus}_{addr:02x}")
            self._abort_if_unique_id_configured()

            error = await _async_validate_i2c(self.hass, model, bus, addr)
            if error:
                errors["base"] = error
            else:
                data: dict[str, Any] = {
                    CONF_NAME: name,
                    CONF_MODEL: model,
                    CONF_BUS: bus,
                    CONF_ADDR: addr,
                }
                if model == MODEL_CLASSIC:
                    data[CONF_MAX_SOC] = user_input.get(CONF_MAX_SOC, DEFAULT_MAX_SOC)
                    if user_input.get(CONF_BATTERY_CAPACITY):
                        data[CONF_BATTERY_CAPACITY] = user_input[CONF_BATTERY_CAPACITY]

                return self.async_create_entry(title=name, data=data)

        schema_fields: dict[Any, Any] = {
            vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
            vol.Required(CONF_BUS, default=DEFAULT_BUS): vol.All(
                vol.Coerce(int), vol.Range(min=0, max=10)
            ),
            vol.Required(
                CONF_ADDR, default=f"0x{_default_addr(model):02x}"
            ): str,
        }
        if model == MODEL_CLASSIC:
            schema_fields[vol.Optional(CONF_MAX_SOC, default=DEFAULT_MAX_SOC)] = (
                vol.All(vol.Coerce(int), vol.Range(min=1, max=100))
            )
            schema_fields[vol.Optional(CONF_BATTERY_CAPACITY)] = vol.All(
                vol.Coerce(int), vol.Range(min=1)
            )

        return self.async_show_form(
            step_id="details",
            data_schema=vol.Schema(schema_fields),
            errors=errors,
            description_placeholders={
                "model": "UPS HAT (E)" if model == MODEL_E else "Classic / (C)",
            },
        )
