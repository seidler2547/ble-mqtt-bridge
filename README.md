# ble-mqtt-bridge
A Python Bluetooth LE to MQTT bridge

Should be run as root or as user with appropriate permissions to start BT LE scans.

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

## Example configuration
### IPV 877710 Cccool Chain Control Bluetooth sensor
```
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
```
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
```
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
