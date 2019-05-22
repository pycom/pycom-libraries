#!/usr/bin/env python
#
# Copyright (c) 2019, Pycom Limited.
#
# This software is licensed under the GNU GPL version 3 or any
# later version, with permitted additional terms. For more information
# see the Pycom Licence v1.0 document supplied with this file, or
# available at https://www.pycom.io/opensource/licensing
#

from machine import UART
import machine
import os
from network import WLAN

uart = UART(0, baudrate=115200)
os.dupterm(uart)

wifi_ssid = 'YOURWIFISSID'
wifi_pass = 'YOURWIFIPASSWORD'

if machine.reset_cause() != machine.SOFT_RESET:
        
    wlan = WLAN(mode=WLAN.STA)
    
    wlan.connect(wifi_ssid, auth=(WLAN.WPA2, wifi_pass), timeout=5000)

    while not wlan.isconnected(): 
         machine.idle()


machine.main('main.py')
