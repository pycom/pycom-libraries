#!/usr/bin/env python
#
# Copyright (c) 2019, Pycom Limited.
#
# This software is licensed under the GNU GPL version 3 or any
# later version, with permitted additional terms. For more information
# see the Pycom Licence v1.0 document supplied with this file, or
# available at https://www.pycom.io/opensource/licensing
#

# See https://docs.pycom.io for more information regarding library specifics

from pycoproc_1 import Pycoproc
from LIS2HH12 import LIS2HH12
from SI7006A20 import SI7006A20
from LTR329ALS01 import LTR329ALS01
from MPL3115A2 import MPL3115A2,ALTITUDE,PRESSURE

py = Pycoproc(Pycoproc.PYSENSE)
mp = MPL3115A2(py,mode=ALTITUDE) # Returns height in meters. Mode may also be set to PRESSURE, returning a value in Pascals
si = SI7006A20(py)
lt = LTR329ALS01(py)
li = LIS2HH12(py)

import _thread
from time import sleep
import uos

def send_sensor_data():
    h2 = None
    t2 = None
    l2 = None
    while (pybytes):
        h = round(si.humidity(),1)
        t = round(si.temperature(),1)
        l = lt.light()
        if h != h2:
            print('humidity', h)
            pybytes.send_signal(1, h)
            h2=h
        if t != t2:
            print('temperature', t)
            pybytes.send_signal(2, t)
            t2=t
        if l != l2:
            print('luminocity', l)
            pybytes.send_signal(3, l)
            l2=l
        sleep(10)

# _thread.start_new_thread(send_sensor_data, ())
send_sensor_data()
