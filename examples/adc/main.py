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

adc = ADC(0)
adc_c = adc.channel(pin='P13')

while True:
    value = adc_c.value()
    print("ADC value:" + str(value))
    time.sleep(1)
