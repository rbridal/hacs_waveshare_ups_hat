"""Unit tests for derived sensor logic (no Home Assistant runtime required)."""

from __future__ import annotations

# Mirror of thresholds in sensor.py so tests stay independent of HA imports.
RECHARGE_THRESHOLD = 95
AC_PRESENT_MV = 1000
DISCHARGE_CURRENT_MA = -10
LOW_BATTERY_PERCENTAGE = 20


def system_state_e(data: dict) -> str:
    """High-level state for UPS HAT (E) — same rules as production."""
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


def charge_current_a(data: dict) -> float | None:
    raw = data.get("battery_current")
    if raw is None:
        return None
    amps = raw * 0.001
    return round(amps, 3) if amps > 0 else 0.0


def discharge_current_a(data: dict) -> float | None:
    raw = data.get("battery_current")
    if raw is None:
        return None
    amps = raw * 0.001
    return round(-amps, 3) if amps < 0 else 0.0


class TestSystemStateE:
    def test_ok_when_ac_and_full(self):
        assert (
            system_state_e(
                {
                    "battery_percent": 100,
                    "vbus_voltage": 15000,
                    "battery_current": 50,
                    "is_charging": True,
                }
            )
            == "ok"
        )

    def test_ok_when_ac_idle_above_threshold(self):
        assert (
            system_state_e(
                {
                    "battery_percent": 98,
                    "vbus_voltage": 15000,
                    "battery_current": 0,
                    "is_charging": False,
                }
            )
            == "ok"
        )

    def test_recharging_when_below_95_and_charging(self):
        assert (
            system_state_e(
                {
                    "battery_percent": 80,
                    "vbus_voltage": 15000,
                    "battery_current": 500,
                    "is_charging": True,
                }
            )
            == "recharging"
        )

    def test_on_battery_when_vbus_zero(self):
        assert (
            system_state_e(
                {
                    "battery_percent": 100,
                    "vbus_voltage": 0,
                    "battery_current": -245,
                    "is_charging": False,
                }
            )
            == "on_battery"
        )

    def test_on_battery_when_discharging_even_if_vbus_present(self):
        assert (
            system_state_e(
                {
                    "battery_percent": 50,
                    "vbus_voltage": 15000,
                    "battery_current": -100,
                    "is_charging": False,
                }
            )
            == "on_battery"
        )

    def test_low_battery_when_discharging_and_low(self):
        assert (
            system_state_e(
                {
                    "battery_percent": 15,
                    "vbus_voltage": 0,
                    "battery_current": -300,
                    "is_charging": False,
                }
            )
            == "low_battery"
        )

    def test_idle_status_with_no_ac_is_on_battery(self):
        """Regression: MCU may report idle while running on battery."""
        assert (
            system_state_e(
                {
                    "battery_percent": 100,
                    "vbus_voltage": 0,
                    "battery_current": -245,
                    "is_charging": False,
                    "status": "idle",
                }
            )
            == "on_battery"
        )


class TestCurrentSplit:
    def test_charge_positive(self):
        assert charge_current_a({"battery_current": 390}) == 0.39
        assert discharge_current_a({"battery_current": 390}) == 0.0

    def test_discharge_negative(self):
        assert charge_current_a({"battery_current": -245}) == 0.0
        assert discharge_current_a({"battery_current": -245}) == 0.245

    def test_zero(self):
        assert charge_current_a({"battery_current": 0}) == 0.0
        assert discharge_current_a({"battery_current": 0}) == 0.0

    def test_none(self):
        assert charge_current_a({}) is None
        assert discharge_current_a({}) is None
