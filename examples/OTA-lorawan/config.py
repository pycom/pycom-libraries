#!/usr/bin/env python
#
# Copyright (c) 2019, Pycom Limited.
#
# This software is licensed under the GNU GPL version 3 or any
# later version, with permitted additional terms. For more information
# see the Pycom Licence v1.0 document supplied with this file, or
# available at https://www.pycom.io/opensource/licensing
#

#LORASERVER configuration
LORASERVER_IP = "127.0.0.1"
LORASERVER_URL = 'http://localhost'
LORASERVER_MQTT_PORT = 1883
LORASERVER_API_PORT = 8080
LORASERVER_USER = 'admin'
LORASERVER_PASS = 'admin'

LORASERVER_SERVICE_PROFILE = 'ota_sp'
LORASERVER_DOWNLINK_DR = 5
LORASERVER_DOWNLINK_FREQ = 869525000
LORASERVER_APP_ID = 1 # Read from Web Interface / Applications

#update configuration
UPDATE_DELAY = 300

