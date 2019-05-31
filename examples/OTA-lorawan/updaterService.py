#!/usr/bin/env python
#
# Copyright (c) 2019, Pycom Limited.
#
# This software is licensed under the GNU GPL version 3 or any
# later version, with permitted additional terms. For more information
# see the Pycom Licence v1.0 document supplied with this file, or
# available at https://www.pycom.io/opensource/licensing
#

import paho.mqtt.client as paho
from ota import OTAHandler
import signal
import time
import config
import sys

exit = False
client = None

def sigint_handler(signum, frame):
    global exit
    exit = True
    print("Terminating Lora OTA updater")
    
def on_message(mosq, ota, msg):
    print("{} {} {}".format(msg.topic, msg.qos, msg.payload))
    ota.process_rx_msg(msg.payload.decode())

def on_publish(mosq, obj, mid):
    pass

if __name__ == '__main__':
    signal.signal(signal.SIGINT, sigint_handler)
    
    ota = OTAHandler()

    client = paho.Client(userdata=ota)
    client.connect(config.LORASERVER_IP, config.LORASERVER_MQTT_PORT, 60)
    
    client.on_message = on_message
    client.on_publish = on_publish
    
    client.subscribe("application/+/device/+/rx", 0)

    ota.set_mqtt_client(client)
    
    while client.loop() == 0 and not exit:
        pass

    ota.stop()
    sys.exit(0)
