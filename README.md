# Cleep

Cleep is a lightweight framework for building Raspberry Pi based IoT devices.

It runs as a system service on a Raspberry Pi, loads small Python applications
called modules, and exposes them through a local web interface and HTTP RPC API.
Modules can add device features such as audio playback, network setup, GPIO
control, sensors, dashboards, updates, or integrations with other services.

The core project provides:

- a Python daemon for starting and supervising modules
- an internal message bus for commands and events
- an HTTP/HTTPS RPC server
- a web UI served from the device
- module installation, update, and uninstall helpers
- common Raspberry Pi helpers for audio, network, files, commands, drivers, and
  configuration

Cleep is useful when you want to turn a Raspberry Pi into a focused appliance,
for example a sensor hub, audio device, home automation controller, or a custom
device similar to a Toniebox.

## Requirements

- Raspberry Pi running Raspberry Pi OS or another Debian-based ARM system
- Python 3.9 or newer
- root access for system service, GPIO, network, and audio configuration
- network access if you want to install modules from remote app sources

This project targets Linux on Raspberry Pi. It is not intended to run directly
on macOS or Windows.

## Install On A Raspberry Pi

Install from a `.deb` package:

```bash
sudo apt update
sudo apt install ./cleep.deb
```

After installation, Cleep is enabled as a system service:

```bash
sudo systemctl status cleep
sudo systemctl restart cleep
```

Open the web interface from another device on the same network:

```text
https://<raspberry-pi-ip>/
```

If HTTPS is not configured or your browser rejects the local certificate, try:

```text
http://<raspberry-pi-ip>/
```

Logs are written to:

```text
/var/log/cleep.log
```

The main configuration file is:

```text
/etc/cleep/cleep.conf
```

Installed modules are loaded from:

```text
/opt/cleep/modules
```

## Build From Source

On a Raspberry Pi:

```bash
sudo apt update
sudo apt install debhelper dh-python python3-all python3-setuptools
git clone https://github.com/CleepDevice/cleep.git
cd cleep
dpkg-buildpackage -us -uc -b
sudo apt install ../cleep_*.deb
```

## How It Works

Cleep starts the core service, reads `/etc/cleep/cleep.conf`, loads configured
modules, then starts the RPC server and web UI.

The default core modules are:

- `system`
- `update`
- `audio`
- `network`
- `cleepbus`
- `parameters`

Additional modules can be installed from Cleep app sources or developed locally.
A module can expose public Python methods as RPC commands, store configuration
in `/etc/cleep`, register devices, send events, and communicate with other
modules through the internal bus.

## Motion Sensor To MQTT Example

This example shows the shape of a simple module that reads a PIR motion sensor
from a Raspberry Pi GPIO pin and publishes an MQTT message when motion is
detected.

Install the Python libraries needed by the module:

```bash
sudo apt install python3-gpiozero python3-paho-mqtt
```

Create a local module directory:

```text
/opt/cleep/modules/motionmqtt/
```

Add `/opt/cleep/modules/motionmqtt/__init__.py`:

```python
APP_FILENAME = "motionmqtt"
```

Add `/opt/cleep/modules/motionmqtt/motionmqtt.py`:

```python
import json
import time

from gpiozero import MotionSensor
import paho.mqtt.client as mqtt

from cleep.core import CleepModule


class Motionmqtt(CleepModule):
    MODULE_DESCRIPTION = "Publish MQTT messages when motion is detected"
    MODULE_AUTHOR = "Cleep"
    MODULE_VERSION = "0.1.0"
    MODULE_CONFIG_FILE = "motionmqtt.json"

    DEFAULT_CONFIG = {
        "enabled": True,
        "pin": 17,
        "mqtt_host": "localhost",
        "mqtt_port": 1883,
        "topic": "home/motion",
        "cooldown_seconds": 10,
    }

    def _configure(self):
        self.sensor = None
        self.client = mqtt.Client()
        self.last_motion_at = 0

    def _on_start(self):
        self._connect_mqtt()
        self._setup_sensor()

    def _on_stop(self):
        if self.sensor:
            self.sensor.close()
        self.client.disconnect()

    def _connect_mqtt(self):
        config = self._get_config()
        self.client.connect(config["mqtt_host"], config["mqtt_port"], 60)

    def _setup_sensor(self):
        config = self._get_config()
        if self.sensor:
            self.sensor.close()

        self.sensor = MotionSensor(config["pin"])
        self.sensor.when_motion = self._motion_detected

    def _motion_detected(self):
        config = self._get_config()
        now = time.time()

        if not config["enabled"]:
            return
        if now - self.last_motion_at < config["cooldown_seconds"]:
            return

        self.last_motion_at = now
        payload = {
            "motion": True,
            "pin": config["pin"],
            "timestamp": int(now),
        }

        self.client.publish(config["topic"], json.dumps(payload), qos=1)
        self.send_event("motionmqtt.motion.detected", payload)

    def update_settings(
        self,
        enabled=None,
        pin=None,
        mqtt_host=None,
        mqtt_port=None,
        topic=None,
        cooldown_seconds=None,
    ):
        config = {}

        if enabled is not None:
            config["enabled"] = enabled
        if pin is not None:
            config["pin"] = pin
        if mqtt_host is not None:
            config["mqtt_host"] = mqtt_host
        if mqtt_port is not None:
            config["mqtt_port"] = mqtt_port
        if topic is not None:
            config["topic"] = topic
        if cooldown_seconds is not None:
            config["cooldown_seconds"] = cooldown_seconds

        self._update_config(config)

        if "mqtt_host" in config or "mqtt_port" in config:
            self.client.disconnect()
            self._connect_mqtt()
        if "pin" in config:
            self._setup_sensor()

        return self._get_config()
```

Enable the module by adding it to the `general.modules` list in:

```text
/etc/cleep/cleep.conf
```

Example:

```ini
[general]
modules = ['motionmqtt']
updated = []
```

Keep any existing modules already listed there.

Restart Cleep:

```bash
sudo systemctl restart cleep
```

When the PIR sensor detects motion, the module publishes a JSON payload to the
configured MQTT topic:

```json
{
  "motion": true,
  "pin": 17,
  "timestamp": 1730000000
}
```

Settings can be changed through the Cleep RPC API. For example, to change the
GPIO pin, MQTT topic, and cooldown:

```bash
curl -k -X POST https://<raspberry-pi-ip>/command \
  -H "Content-Type: application/json" \
  -d '{
    "to": "motionmqtt",
    "command": "update_settings",
    "params": {
      "pin": 23,
      "topic": "kids-room/motion",
      "cooldown_seconds": 30
    }
  }'
```

The module saves those settings to:

```text
/etc/cleep/motionmqtt.json
```

You can also add a small web UI for the module under `/opt/cleep/html` so the
same settings can be changed from the browser.

## Development

Run unit tests from the project root:

```bash
python3 -m unittest discover -s cleep/tests -p "test_*.py"
```

For local module development, place modules under `/opt/cleep/modules`. A module
usually contains:

```text
module_name/
  __init__.py
  module_name.py
```

The class name must match the module filename with the first letter capitalized.
For example, `motionmqtt.py` defines `class Motionmqtt`.

## Contributing

Contributions are welcome. Please keep changes focused, include tests when
possible, and document user-visible behavior.

## License

Cleep is released under the GPL-3.0-or-later license. See `LICENSE` for details.
