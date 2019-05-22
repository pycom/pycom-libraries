#!/usr/bin/env python
#
# Copyright (c) 2019, Pycom Limited.
#
# This software is licensed under the GNU GPL version 3 or any
# later version, with permitted additional terms. For more information
# see the Pycom Licence v1.0 document supplied with this file, or
# available at https://www.pycom.io/opensource/licensing
#

from machine import ADC
import time

class ALSPT19(object):
    def __init__(self, pin_name):
        adc = ADC()
        self.pin = adc.channel(pin=pin_name, attn=ADC.ATTN_11DB, bits=12)
        self.threshold = None

    def calibrate(self, samples=300):
        max_val = 0
        for _ in range(samples):
            val = self.pin()
            if val > max_val:
                max_val = val
            time.sleep_ms(10)

        self.threshold = max_val * 1.2

    def is_on(self):
        if self.pin() > self.threshold:
            return True
        return False
