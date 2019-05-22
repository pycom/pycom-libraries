#!/usr/bin/env python
#
# Copyright (c) 2019, Pycom Limited.
#
# This software is licensed under the GNU GPL version 3 or any
# later version, with permitted additional terms. For more information
# see the Pycom Licence v1.0 document supplied with this file, or
# available at https://www.pycom.io/opensource/licensing
#

''' Set here you setup config in this example
'''
CONFIG = {
    'wifi_ssid': "somewifi",
    'wifi_password': 'iforgot',
    'ntp_server': 'time.google.com',
    'project_id': 'pybytes-101', # replace with your Google project_id
    'cloud_region': 'us-central1', # replace
    'registry_id': 'goinvent', # replace with your Google registry_id
    'topic': '/devices/pysense2/events', # replace so match your device
    'device_id': 'pysense2' #
}
