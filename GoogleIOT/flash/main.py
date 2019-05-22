#!/usr/bin/env python
#
# Copyright (c) 2019, Pycom Limited.
#
# This software is licensed under the GNU GPL version 3 or any
# later version, with permitted additional terms. For more information
# see the Pycom Licence v1.0 document supplied with this file, or
# available at https://www.pycom.io/opensource/licensing
#

''' Example Google IoT Core connection
'''
import utime
import machine
import _thread
from network import WLAN
from google_iot_core import GoogleMQTTClient
from config import CONFIG

# Connect to Wifi
WLAN_I = WLAN(mode=WLAN.STA, max_tx_pwr=78)
print('Connecting to WiFi %s' % CONFIG.get('wifi_ssid'))
WLAN_I.connect(CONFIG.get('wifi_ssid'), (WLAN.WPA2, CONFIG.get('wifi_password')), timeout=60000)
i = 0
while not WLAN_I.isconnected():
    i = i + 1
    # print(".", end="")
    utime.sleep(1)
    if i > 60:
        print("\nWifi not available")
        break

# Syncing time
RTCI = machine.RTC()
print('Syncing time with %s' % CONFIG.get('ntp_server'), end='')
RTCI.ntp_sync(CONFIG.get('ntp_server'))
while not RTCI.synced():
    print('.', end='')
    utime.sleep(1)
print('')

# read the private key
FILE_HANDLE = open("cert/%s-pk8.key" % CONFIG.get('device_id'))
PRIVATE_KEY = FILE_HANDLE.read()
FILE_HANDLE.close()

# make a mqtt client, connect and publish an empty message
MQTT_CLIENT = GoogleMQTTClient(CONFIG.get('project_id'),
                               PRIVATE_KEY,
                               CONFIG.get('cloud_region'),
                               CONFIG.get('registry_id'),
                               CONFIG.get('device_id'))


MQTT_CLIENT.connect()
MQTT_CLIENT.publish(CONFIG.get('topic'), b'test')

# make a demo callback
def _sub_cb(topic, msg):
    ''' handle your message received here ...
    '''
    print('received:', topic, msg)

# register callback
MQTT_CLIENT.set_callback(_sub_cb)

# example subscription
MQTT_CLIENT.subscribe('/devices/%s/config' % CONFIG.get('device_id'), qos=1)
while True:
    # Non-blocking wait for message
    MQTT_CLIENT.check_msg()
    # Then need to sleep to avoid 100% CPU usage (in a real
    # app other useful actions would be performed instead)
    utime.sleep_ms(100)
