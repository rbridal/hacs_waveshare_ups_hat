# Waveshare UPS HAT Integration for Home Assistant

This integration allows you to monitor [Waveshare UPS Hat](https://www.waveshare.com/wiki/UPS_HAT) (and UPS HAT **E**) status in your Home Assistant instance.

This repository is the actively maintained continuation of the original project by [@mykhailog](https://github.com/mykhailog/hacs_waveshare_ups_hat). It includes support for the UPS HAT (E) model (contributed by [@andriyor](https://github.com/andriyor)).

<img src="https://user-images.githubusercontent.com/1454659/114266149-595d6280-99fd-11eb-9056-dd0fbe178ecc.png" width="400" />

## Installation

### HACS

If you use [HACS](https://hacs.xyz/) you can install and update this component.

1. Go into **HACS → Custom repositories** and add:
   - URL: `https://github.com/rbridal/hacs_waveshare_ups_hat`
   - Type: **Integration**
2. Go to Integrations, search for **waveshare_ups_hat**, and click **Install**.

### Manual

Download and unzip or clone this repository and copy `custom_components/waveshare_ups_hat/` to your configuration directory of Home Assistant, e.g. `~/.homeassistant/custom_components/`.

In the end your file structure should look like this:

```
~/.homeassistant/custom_components/waveshare_ups_hat/__init__.py
~/.homeassistant/custom_components/waveshare_ups_hat/manifest.json
~/.homeassistant/custom_components/waveshare_ups_hat/sensor.py
~/.homeassistant/custom_components/waveshare_ups_hat/binary_sensor.py
~/.homeassistant/custom_components/waveshare_ups_hat/const.py
~/.homeassistant/custom_components/waveshare_ups_hat/ina219.py
~/.homeassistant/custom_components/waveshare_ups_hat/ups_hat_e.py
```

## Configuration

### Classic UPS HAT / UPS HAT (C) (INA219-based)

Create a sensor entry in your `configuration.yaml`:

```yaml
sensor:
  - platform: waveshare_ups_hat
    name: UPS                    # Optional
    unique_id: waveshare_ups     # Optional
```

The following data can be read:

- SoC (State of Charge)
- PSU Voltage
- Shunt Voltage
- Current
- Power
- Charging Status
- Online Status
- Is Low Battery (< 20%)

If you consistently experience capacity below 100% when the device is fully charged, you can adjust it using the `max_soc` property:

```yaml
sensor:
  - platform: waveshare_ups_hat
    max_soc: 91
```

Optional `battery_capacity` (mAh) enables remaining capacity / remaining time estimates.

### UPS HAT (E)

The (E) model uses a different on-board MCU (I2C address `0x2d`) instead of an INA219. Add the `model: e` option:

```yaml
sensor:
  - platform: waveshare_ups_hat
    name: UPS E
    unique_id: waveshare_ups_e
    model: e
```

This exposes individual sensors for:

- Battery %
- Battery voltage / current
- VBUS voltage / current / power
- Remaining capacity (mAh)
- Time to empty / time to full
- Charging status
- Individual cell voltages (1–4)

### Binary Sensor

You may also create a binary sensor that is “on” when the UPS is online and “off” otherwise:

```yaml
binary_sensor:
  - platform: waveshare_ups_hat
```

## Enabling I2C / smbus support on Raspberry Pi

### Home Assistant OS

To enable I2C in Home Assistant OS follow the [official instructions](https://www.home-assistant.io/common-tasks/os/#enable-i2c) or use the [HassOS I2C Configurator add-on](https://community.home-assistant.io/t/add-on-hassos-i2c-configurator/264167).

### Home Assistant Core / Raspberry Pi OS

Enable the I2C interface:

```bash
sudo raspi-config
```

Select **Interfacing Options → I2C → Yes**, then reboot.

Install dependencies and add the `homeassistant` user to the `i2c` group:

```bash
sudo apt-get install build-essential libi2c-dev i2c-tools python3-dev libffi-dev
sudo addgroup homeassistant i2c
sudo reboot
```

#### Check the I2C address of the sensor

```bash
/usr/sbin/i2cdetect -y 1
```

Typical addresses:

- Classic UPS HAT / (C): often `0x42` (INA219)
- UPS HAT (E): `0x2d`

Example output:

```text
     0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
00:          -- -- -- -- -- -- -- -- -- -- -- -- --
10: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
20: -- -- -- 23 -- -- -- -- -- -- -- -- -- -- -- --
30: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
40: 40 -- -- -- -- -- UU -- -- -- -- -- -- -- -- --
50: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
60: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
70: -- -- -- -- -- -- -- 77
```

## Credits

- Original integration by [@mykhailog](https://github.com/mykhailog)
- UPS HAT (E) support by [@andriyor](https://github.com/andriyor)
- Maintained by [@rbridal](https://github.com/rbridal)

## License

MIT
