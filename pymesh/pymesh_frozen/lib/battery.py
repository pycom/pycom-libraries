'''
Copyright (c) 2020, Pycom Limited.
This software is licensed under the GNU GPL version 3 or any
later version, with permitted additional terms. For more information
see the Pycom Licence v1.0 document supplied with this file, or
available at https://www.pycom.io/opensource/licensing
'''

import machine
from machine import Timer,Pin,ADC
import time

__version__ = '1'
"""
__version__ = '1'
* first release

"""
class Battery:
    def __init__(self):
        self.init = False
        self.adc = machine.ADC()
        self.apin = self.adc.channel(pin='P16', attn=self.adc.ATTN_11DB)
        self.val = self.apin.voltage()
        print("bat:", self.val)

    def get_battery_level(self):
        self.val = self.apin.voltage()
        print("bat:", self.val)
        battery_percentage = self.val/3300
        if battery_percentage <= 0.25:
            battery_percentage = 0.25
        elif battery_percentage > 0.25 and battery_percentage <= 0.5:
            battery_percentage = 0.5
        elif battery_percentage > 0.5 and battery_percentage <= 0.75:
            battery_percentage = 0.75
        elif battery_percentage <= 1:
            battery_percentage = 1
        return int(battery_percentage*100)
