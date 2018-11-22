# ble-mqtt-bridge
A Python Bluetooth LE to MQTT bridge

Should be run as root or as user with appropriate permissions to start BT LE scans.

__Last time I tried, the MQTT server built into HA did not support the MQTT protocol fully. So use Mosquitto or another full-featured MQTT server instead!__

Needs `paho.mqtt.client` and `bluepy`.

## Run the bridge
Run like this:
```
source /opt/ble-mqtt/bin/activate ; /opt/ble-mqtt/ble-mqtt-bridge.py
```

## Run the watcher
There is a watcher script which I need because I use a Intel AC7260 card for Bluetooth, which crashes quite often. The script works around that by waiting for too many errors or too little activity (sometimes the card stops responding to anything and doesn't even report scan results).
It then removes the btusb modules, waits 5 seconds for USB autosuspend to kick in and then reloads the module. This prevents BT failures very reliably for me.

Run as
```
source /opt/ble-mqtt/bin/activate ; /opt/ble-mqtt/watcher.py
```

## Use config file
To allow for easy configuration, the bridge expects `./config/ble-mqtt-conf.json` to exist. Generally, the config can be split into 3 parts: `mqtt`, `scan` and `knownDevices`.


`mqtt` contains broker related information (`host`, `port`, `user`, `password`). All values can be omitted for hard-coded default values. 

`scan` controls BLE scanning. If both `initial` and `loop` are set to false, no BLE scanning will take place, thus not requiring root. `timeout` is configurable in seconds.

`knownDevices` can be used to map BLE device ``MACs``, ``UUIDs`` and ``handles`` to human-readable names. If not set, the broker will simply not translate and use the values from MQTT. If a ``handle`` is defined for a characteristic (``UUID`` or ``name``), the broker will always use the given handle as it gives a much better performance.

### Example config
This example config contains the default values for `mqtt` and `scan`. 
```json
{
    "mqtt": {
        "host": "localhost",
        "port": "1883",
        "user": "",
        "password": ""
    },
    "scan": {
        "initial": true,
        "loop": false,
        "timeout": 5
    },
    "knownDevices": [
        {
            "mac": "11:11:11:11:11:11",
            "name": "livingroom",
            "characteristics": [
                { "uuid": "47e9ee2b-47e9-11e4-8939-164230d1df67", "handle": "0x003d", "name": "temperature" },
                { "uuid": "47e9ee30-47e9-11e4-8939-164230d1df67", "handle": "0x0048", "name": "pin" },
            ]
        },
        {
            "mac": "22:22:22:22:22:22",
            "name": "bedroom",
            "characteristics": [
              ...
            ]
        }
    ]
}
```
## Run in Docker
To run the bridge in a Docker container, use the `Dockerfile` to build your own container, e.g. using:
```docker
docker build -t "ble-mqtt-bridge:rpi-latest" .
```
When running the container, some options need to be considered: 
| Option | Description |
|-|-|
|`--net host` | allow bluetooth access on host|
|`--privileged` | allow BLE scans (needs root) |
|`-v /path/to/config/:/app/config/` | bind your local config file to the container |
```docker
docker run -dit \
--net host \
--name ble-mqtt-bridge \
-v home/pi/ble-mqtt-bridge/config/:/app/config/ \
ble-mqtt-bridge:rpi-latest
```
Build and run has been tested using a Raspberry Pi 3 B+ using Raspbian Strech Lite.



## Example Home Assistant configuration
### IPV 877710 Cccool Chain Control Bluetooth sensor
```yaml
sensor:
  - platform: mqtt
    state_topic: "ble/88:4a:ea:bb:bb:bb/advertisement/ff"
    name: 'Sensor 1'
    unit_of_measurement: '°C'
    value_template: >-
      {% if value[0:2]|int(base=16) is lessthan(128) %}
      {{ value[0:2]|int(base=16)|float + value[2:4]|int(base=16)|float/256 }}
      {% else %}
      {{ value[0:2]|int(base=16)|float + value[2:4]|int(base=16)|float/256 - 256.0 }}
      {% endif %}
```

### April Brother ABTemp Temperature BLE Sensor Beacon
```yaml
sensor:
  - platform: mqtt
    state_topic: "ble/12:3b:6a:cc:cc:cc/advertisement/ff"
    name: 'Beacon SZ'
    unit_of_measurement: '°C'
    value_template: >-
      {% if value[0:2] == '4c' %}
      {{ value[46:48]|int(base=16)|float }}
      {% else %}
      {{ states.sensor.beacon_sz.state }}
      {% endif %}
```
### April Brother Smart BLE Accelerometer iBeacon Beacon Sensor
```yaml
sensor:
- platform: mqtt
    state_topic: "ble/12:3b:6a:dd:dd:dd/advertisement/ff"
    name: 'Blue Beacon'
    unit_of_measurement: '°C'
    value_template: >-
      {% if value[0:2] == 'd2' %}
      {{ value[18:20]|int(base=16)|float }}
      {% else %}
      {{ states.sensor.blue_beacon.state }}
      {% endif %}
```
### Comet Blue BLE thermostat (using https://github.com/seidler2547/home-assistant-cc)
```yaml
climate:
  - platform: sygonix
    devices: 
      Livingroom:
        mac: livingroom
        pin: 000000

```