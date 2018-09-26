# See https://docs.pycom.io for more information regarding library specifics

from pysense import Pysense
from LIS2HH12 import LIS2HH12
from SI7006A20 import SI7006A20
from LTR329ALS01 import LTR329ALS01
from MPL3115A2 import MPL3115A2,ALTITUDE,PRESSURE

py = Pysense()
mp = MPL3115A2(py,mode=ALTITUDE) # Returns height in meters. Mode may also be set to PRESSURE, returning a value in Pascals
si = SI7006A20(py)
lt = LTR329ALS01(py)
li = LIS2HH12(py)

import _thread
from time import sleep
import uos

def send_sensor_data():
    while (pybytes):
        pybytes.send_virtual_pin_value(True, 1, si.humidity())
        pybytes.send_virtual_pin_value(True, 2, si.temperature())
        pybytes.send_virtual_pin_value(True, 3, lt.light())
        sleep(10)

_thread.start_new_thread(send_sensor_data, ())
