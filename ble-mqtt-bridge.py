#!/usr/bin/env python3

import paho.mqtt.client as mqtt
import sys
import gc
import json
import argparse
import datetime
from threading import Thread, Semaphore
from concurrent.futures import ThreadPoolExecutor
from time import sleep
from bluepy.btle import Scanner, DefaultDelegate, Peripheral

with open('config/ble-mqtt-conf.json', 'r') as f:
    config = json.load(f)

MQTT_HOST = config.get("mqtt", {}).get("host", "localhost")
MQTT_PORT = int(config.get("mqtt", {}).get("port", 1883))
MQTT_USER = config.get("mqtt", {}).get("user", "")
MQTT_PASSWORD = config.get("mqtt", {}).get("password", "")

SCAN_INITIAL = bool(config.get("scan", {}).get("initial", True))
SCAN_LOOP = bool(config.get("scan", {}).get("loop", False))
SCAN_TIMEOUT = int(config.get("scan", {}).get("timeout", 5))

KNOWN_DEVICES = config.get("knownDevices", [])

client = mqtt.Client()
# Check if MQTT user and/or password are specified
if len(MQTT_USER) > 0 or len(MQTT_PASSWORD) > 0:
    client.username_pw_set(MQTT_USER, MQTT_PASSWORD)

class ScanDelegate(DefaultDelegate):
    ''' Publishes scan results to MQTT '''
    def __init__(self):
        DefaultDelegate.__init__(self)

    def handleDiscovery(self, dev, isNewDev, isNewData):
        ''' Called when BLE advertising reports are received '''
        try:
            # publish the RSSI
            client.publish('ble/{}/rssi'.format(dev.addr), dev.rssi)
            # just some info/debug print
            print("dev {} rssi {}".format(dev.addr, dev.rssi))
            # publish all values individually
            for d in dev.getScanData():
                client.publish('ble/{}/advertisement/{:02x}'.format(dev.addr, d[0]), d[2])
            # publish a JSON map of all values
            scan_map = { d[1]: d[2] for d in dev.getScanData() }
            client.publish('ble/{}/advertisement/json'.format(dev.addr), json.dumps(scan_map))
        except Exception as e:
            # report errors
            client.publish('ble/{}/error', str(e))
            sleep(1)

class NotificationDelegate(DefaultDelegate):
    ''' Publishes notifications to MQTT '''
    def __init__(self, addr):
        DefaultDelegate.__init__(self)
        self._addr = addr

    def handleNotification(self, cHandle, data):
        ''' Called when BLE notifications are received '''
        try:
            # publish the data
            client.publish('ble/{}/notification/{}'.format(self._addr, cHandle), data)
        except Exception as e:
            # report errors
            client.publish('ble/{}/error', str(e))
            sleep(1)

class ScannerThread(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.daemon = True
        self.start()

    def run(self):
        while True:
            try:
                scanner = Scanner().withDelegate(ScanDelegate())
                scanner.scan(20)
            except Exception as e:
                client.publish('ble/scanning/error', str(e))
                sleep(10)
            finally:
                try:
                    scanner.stop()
                except:
                    pass

ble_map_lock = Semaphore()
ble_dev_map = {}

class BLEConnection():
    def __init__(self, mac):
        self._mac = mac
        self._deviceInfo = None
        for device in KNOWN_DEVICES:
            if mac == device['name']:
                self._mac = device['mac']
                self._deviceInfo = device
        self._name = self._deviceInfo.get('name', mac) if self._deviceInfo is not None else mac
        self.connected = False

    def process_commands(self, command_list):
        try:
            print("Connecting to {} ({})".format(self._name, self._mac))
            skey = '{}_semaphore'.format(self._mac)
            with ble_map_lock:
                if skey not in ble_dev_map:
                    ble_dev_map[skey] = Semaphore()
            with ble_dev_map[skey]:
                p = Peripheral(self._mac)
                print("Connected to {} ({})".format(self._name, self._mac))
                for command in command_list:
                    print("  Command {}".format(command))
                    if 'action' in command:
                        action = command['action']

                        handle = None
                        if 'handle' in command:
                            handle = int(command['handle'], 0)
                        uuid = None
                        if 'uuid' in command:
                            uuid = command['uuid']
                        characteristic = None
                        if 'characteristic' in command:
                            characteristic = command['characteristic']

                        if characteristic is not None and self._deviceInfo['characteristics'] is not None:
                            for dev_char in self._deviceInfo['characteristics']:
                                if characteristic == dev_char.get('name', None):
                                    handle = int(dev_char.get('handle'), 0) if dev_char.get('handle', None) is not None else None 
                                    uuid = dev_char.get('uuid', None)

                        if ((uuid is not None or handle is not None) and characteristic is None):
                            characteristic = "{:02x}".format(handle) if handle is not None else uuid

                        ignoreError = None
                        if 'ignoreError' in command:
                            ignoreError = 1

                        if 'value' in command:
                            value = command['value']
                            if type(value) is str:
                                value = value.encode('utf-8')
                            elif type(value) is list:
                                value = bytes(value)

                        try:
                            if  action == 'writeCharacteristic':
                                if handle is not None:
                                    print("    Write {} to {:02x}".format(value, handle))
                                    p.writeCharacteristic(handle, value, True)
                                elif uuid is not None:
                                    for c in p.getCharacteristics(uuid=uuid):
                                        print("    Write {} to {}".format(value, uuid))
                                        c.write(value, True)
                            elif action == 'readCharacteristic':
                                if handle is not None:
                                    result = p.readCharacteristic(handle)
                                    print("    Read {} from {} ({:02x})".format(str(result), characteristic, handle))
                                    client.publish('ble/{}/data/{}'.format(self._name, characteristic), json.dumps([ int(x) for x in result ]), retain=True)
                                elif uuid is not None:
                                    for c in p.getCharacteristics(uuid=uuid):
                                        result = c.read()
                                        print("    Read {} from {} ({})".format(str(result), characteristic, uuid))
                                        client.publish('ble/{}/data/{}'.format(self._name, characteristic), json.dumps([ int(x) for x in result ]), retain=True)
                        except Exception as e:
                            if not ignoreError:
                                raise e
                p.disconnect()
                print("Disconnected from {} ({})".format(self._name, self._mac))
        except Exception as e:
            # report errors
            client.publish('ble/scan/error', str(e))
            sleep(1)

bt_thread_pool = ThreadPoolExecutor(max_workers=2)

class CommandThread(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.daemon = True
        client.on_connect = CommandThread.on_connect
        client.on_message = CommandThread.on_message
        self.start()

    def run(self):
        while True:
            sleep(10)

    # The callback for when the client receives a CONNACK response from the server.
    def on_connect(client, userdata, flags, rc):
        print("Connected with result code "+str(rc))
        # Subscribing in on_connect() means that if we lose the connection and
        # reconnect then subscriptions will be renewed.
        (result, mid) = client.subscribe("ble/+/commands")
        print("Subscribed {}/{} ".format(result, mid))

    # The callback for when a PUBLISH message is received from the server.
    def on_message(client, userdata, msg):
        bt_thread_pool.submit(CommandThread.process_message, client, userdata, msg)

    def process_message(client, userdata, msg):
        topic = msg.topic.split('/')
        print(msg.topic+" "+str(msg.payload))
        print("  using {}/{}/{} len={}".format(topic[0], topic[1], topic[2], len(topic)))
        if len(topic) == 3 and topic[0] == 'ble' and topic[1] == 'scan' and topic[2] == 'commands':
            print (topic)
            try:
                with ble_map_lock:
                    for v in ble_dev_map.values():
                        v.acquire()
                    print("    starting scan")
                    scanner = Scanner().withDelegate(ScanDelegate())
                    scanner.scan(int(msg.payload))
            except Exception as e:
                client.publish('ble/scanning/error', str(e))
                sleep(12)
            finally:
                with ble_map_lock:
                    for v in ble_dev_map.values():
                        v.release()
                try:
                    print("    stopping scan")
                    scanner.stop()
                except:
                    pass
                if SCAN_LOOP:
                    sleep(8)
                    client.publish(topic=msg.topic, payload=msg.payload, qos=msg.qos, retain=msg.retain)
        elif len(topic) == 3 and topic[0] == 'ble' and topic[2] == 'commands':
            try:
                data = json.loads(msg.payload.decode('utf-8'))
                try:
                    conn = BLEConnection(topic[1])
                    conn.process_commands(data['commands'])
                except Exception as e:
                    print('Error: {}'.format(str(e)))
                    if 'tries' in data:
                        if data['tries'] > 1:
                            data['tries'] -= 1
                            # sleep here to give the BT some rest
                            sleep(10)
                            # then try again
                            client.publish(topic=msg.topic, payload=json.dumps(data), qos=msg.qos, retain=msg.retain)
                            return
            except Exception as e2:
                print('Error: {}'.format(str(e2)))

# start the BLE scan and let it run continously

#ScannerThread()
CommandThread()

client.connect(MQTT_HOST, MQTT_PORT)
client.loop_start()
sleep(1)
if SCAN_INITIAL:
    client.publish('ble/scan/commands', SCAN_TIMEOUT)
#client.loop_forever()

while True:
    print("Waiting...")
    sleep(1)
