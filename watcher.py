#!/usr/bin/env python3

import sys
import paho.mqtt.client as mqtt
from datetime import datetime
import time
from subprocess import call
lastseen = datetime.now()
#call(["ls", "-l"])

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))
    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe("ble/+/advertisement/json")

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    global lastseen
    lastseen = datetime.now()
    print(msg.topic)
    if msg.topic == 'ble/scanning/error' and msg.payload.decode('utf-8') == 'Unexpected response (stat)':
        #print(msg.topic+" "+msg.payload.decode('utf-8'))
        print("Oops2")
        #call(["hciconfig", "hci0", "down"])
            #time.sleep(1)
        #call(["rmmod", "btusb"])
        #time.sleep(5)
        #call(["modprobe", "btusb"])
        #time.sleep(1)
        #call(["hciconfig", "hci0", "up"])

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect("localhost", 1883, 60)

    # Blocking call that processes network traffic, dispatches callbacks and
# handles reconnecting.
# Other loop*() functions are available that give a threaded interface and a
# manual interface.
client.loop_start()

while True:
    print("Watching {}".format(datetime.now() - lastseen))
    time.sleep(5)
    if (datetime.now() - lastseen).total_seconds() > 300:
        print("Oops {}".format(datetime.now() - lastseen))
        call(["hciconfig", "hci0", "down"])
        time.sleep(1)
        call(["rmmod", "btusb"])
        time.sleep(5)
        call(["modprobe", "btusb"])
        time.sleep(1)
        call(["hciconfig", "hci0", "up"])
        lastseen = datetime.now()
