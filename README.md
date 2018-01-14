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
