# Waveshare UPS HAT Integration for Home Assistant

This integration allows you to monitor [Waveshare UPS Hat](https://www.waveshare.com/wiki/UPS_HAT) (and UPS HAT **E**) status in your Home Assistant instance.

This repository is the actively maintained continuation of the original project by [@mykhailog](https://github.com/mykhailog/hacs_waveshare_ups_hat). It includes support for the UPS HAT (E) model (contributed by [@andriyor](https://github.com/andriyor)).

<img src="https://user-images.githubusercontent.com/1454659/114266149-595d6280-99fd-11eb-9056-dd0fbe178ecc.png" width="400" />

## Installation

### HACS

1. Go into **HACS → Custom repositories** and add:
   - URL: `https://github.com/rbridal/hacs_waveshare_ups_hat`
   - Type: **Integration**
2. Search for **Waveshare UPS Hat** and install it.
3. Restart Home Assistant.

### Manual

Copy `custom_components/waveshare_ups_hat/` into your Home Assistant `custom_components` directory and restart.

## Configuration (UI)

**YAML platform configuration is no longer used.** Setup is done entirely in the UI.

1. Go to **Settings → Devices & services → Add integration**
2. Search for **Waveshare UPS Hat**
3. Choose your model:
   - **UPS HAT (E)** — MCU at I2C `0x2d`
   - **Classic / UPS HAT (C)** — INA219 (typically `0x42`)
4. Enter a name, I2C bus (usually `1`), and address if needed
5. For classic models you can optionally set max SoC and battery capacity (mAh)

The integration creates a **device** with all related sensors and binary sensors attached to it.

### Migrating from YAML

If you previously used YAML like:

```yaml
sensor:
  - platform: waveshare_ups_hat
    name: UPS
    unique_id: waveshare_ups
    model: e
```

1. Remove those `sensor:` / `binary_sensor:` platform entries from `configuration.yaml`
2. Restart Home Assistant
3. Add the integration via the UI as described above
4. Delete any leftover orphaned entities from the old setup if they remain

### Entities (UPS HAT E)

| Entity | Description |
|--------|-------------|
| Battery | State of charge (%) |
| Battery voltage / current | Pack voltage and current |
| VBUS voltage / current / power | USB-C / input side |
| Remaining capacity | mAh |
| Time to empty / full | Minutes (when applicable) |
| Status | `charging` / `fast_charging` / `discharging` / `idle` |
| Cell voltage 1–4 | Individual cell voltages |
| Online | Power present (not on battery only) |
| Charging | Battery is charging |

### Entities (Classic / C)

Battery %, PSU / load / shunt voltage, current, power, remaining capacity & time (if capacity configured), online, charging, and low-battery binary sensors.

## Enabling I2C

### Home Assistant OS

Follow the [official I2C instructions](https://www.home-assistant.io/common-tasks/os/#enable-i2c) or use the [HassOS I2C Configurator add-on](https://community.home-assistant.io/t/add-on-hassos-i2c-configurator/264167).

### Home Assistant Core / Raspberry Pi OS

```bash
sudo raspi-config   # Interfacing Options → I2C → Yes
sudo apt-get install i2c-tools
sudo addgroup homeassistant i2c
sudo reboot
```

Scan for the device:

```bash
/usr/sbin/i2cdetect -y 1
```

Typical addresses: **0x2d** (E model), **0x42** (classic INA219).

## Credits

- Original integration by [@mykhailog](https://github.com/mykhailog)
- UPS HAT (E) support by [@andriyor](https://github.com/andriyor)
- Maintained by [@rbridal](https://github.com/rbridal)

## License

MIT
