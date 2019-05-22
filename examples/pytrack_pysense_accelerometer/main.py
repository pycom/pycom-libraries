#!/usr/bin/env python
#
# Copyright (c) 2019, Pycom Limited.
#
# This software is licensed under the GNU GPL version 3 or any
# later version, with permitted additional terms. For more information
# see the Pycom Licence v1.0 document supplied with this file, or
# available at https://www.pycom.io/opensource/licensing
#

import time

# From:https://github.com/pycom/pycom-libraries
from LIS2HH12 import LIS2HH12
from pytrack import Pytrack

py = Pytrack()
acc = LIS2HH12()
while True:
    pitch = acc.pitch()
    roll = acc.roll()
    print('{},{}'.format(pitch,roll))
    time.sleep_ms(100)
