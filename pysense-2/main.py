#!/usr/bin/env python
#
# Copyright (c) 2020, Pycom Limited.
#
# This software is licensed under the GNU GPL version 3 or any
# later version, with permitted additional terms. For more information
# see the Pycom Licence v1.0 document supplied with this file, or
# available at https://www.pycom.io/opensource/licensing
#

# See https://docs.pycom.io for more information regarding library specifics

import time
import pycom
import struct
from machine import Pin
from pysense import Pysense
import machine

from LIS2HH12 import LIS2HH12
from SI7006A20 import SI7006A20
from LTR329ALS01 import LTR329ALS01
from MPL3115A2 import MPL3115A2,ALTITUDE,PRESSURE

# This script demonstrates two examples:
# * go to ultra low power mode (~10uA @3.75V) with all sensors, incl accelerometer and also pycom module (Fipy, Gpy, etc) off
# * go to low power mode (~165uA @3.75V) with accelerometer on, pycom module in deepsleep and wake from accelerometer interrupt
wake_from_accelerometer = True
sleep_time_s = 300

def accelerometer():
    print("ACCELEROMETER:", "accel:", accelerometer_sensor.acceleration(), "roll:", accelerometer_sensor.roll(), "pitch:", accelerometer_sensor.pitch(), "x/y/z:", accelerometer_sensor.x, accelerometer_sensor.y, accelerometer_sensor.z )

def activity_int_handler(pin_o):
    if pin_o():
        print('[Activity]')
        # blue
        pycom.rgbled(0x00000A)
    else:
        print('[Inactivity]')
        # yellow
        pycom.rgbled(0x0A0A00)

def activity_int_handler_none(pin_o):
    pass

def blink(ct=5, color=0x220022, on_ms=100, off_ms=100 ):
    while ct >= 0 :
        ct -= 1
        pycom.rgbled(color)
        time.sleep_ms(on_ms)
        pycom.rgbled(0x000000)
        time.sleep_ms(off_ms)

def wait(color=0x0a0a0a):
    print("wait for button ...")
    blink(5, color)
    pycom.rgbled(color)
    ct = 0
    while True:
        if pycoproc.button_pressed():
            blink(5, color)
            print("button pressed")
            break
        time.sleep(0.1)
        ct += 1
        if ct % 10 == 0:
            print('.', end='')
            pycom.rgbled(color)

###############################################################
pycom.heartbeat(False)
pycom.rgbled(0x0a0500)

try:
    print("lte deinit")
    from network import LTE
    lte = LTE()
    lte.deinit()
except:
    pass

pycom.rgbled(0x0a0a0a)
print("pycoproc init")
pycoproc = Pysense()

b = pycoproc.read_battery_voltage()
print("battery {:.2f} V".format(b))

pycoproc.setup_sleep(sleep_time_s)

wait(0x000a00) # blink green, wait for user to press MCLR button, blink green

accelerometer_sensor = LIS2HH12()
accelerometer()

if wake_from_accelerometer == True:
    # configure accelerometer interrupt sensitivity

    # accelerometer_sensor.enable_activity_interrupt(8000, 200, activity_int_handler) # low sensitivty
    # 2000mG (2G), 200ms
    # accelerometer_sensor.enable_activity_interrupt(2000, 200, activity_int_handler) # medium sensitivity
    accelerometer_sensor.enable_activity_interrupt( 100, 200, activity_int_handler) # high sensitivity
    # accelerometer_sensor.enable_activity_interrupt(63, 160, activity_int_handler) # ultra sensitivty

    wait(0x0A000A) # blink purple, wait for user to press MCLR button, blink purple

    print("enable pycom module to wake up from accelerometer interrupt")
    wake_pins = [Pin('P13', mode=Pin.IN, pull=Pin.PULL_DOWN)]
    machine.pin_sleep_wakeup(wake_pins, machine.WAKEUP_ANY_HIGH, True)

    print("put pycoproc to sleep")
    pycoproc.go_to_sleep(pycom_module_off=False, accelerometer_off=False, wake_interrupt=True)

    print("put pycom module to deepsleep", sleep_time_s, "s")
    machine.deepsleep(sleep_time_s * 1000)
else:
    print("put pycoproc to sleep, turn off everything")
    pycoproc.go_to_sleep()

print("we never reach here!")
