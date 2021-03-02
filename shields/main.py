#!/usr/bin/env python
#
# Copyright (c) 2020, Pycom Limited.
#
# This software is licensed under the GNU GPL version 3 or any
# later version, with permitted additional terms. For more information
# see the Pycom Licence v1.0 document supplied with this file, or
# available at https://www.pycom.io/opensource/licensing
#

# This script demonstrates two examples:
# * go to ultra low power mode (~10uA @3.75V) with all sensors, incl accelerometer and also pycom module (Fipy, Gpy, etc) off - tap the MCLR button for this
# * go to low power mode (~165uA @3.75V) with accelerometer on, pycom module in deepsleep and wake from accelerometer interrupt - hold the MCLR button down for this

# See https://docs.pycom.io for more information regarding library specifics

import time
import pycom
import struct
from machine import Pin
from pycoproc import Pycoproc
import machine
from LIS2HH12 import LIS2HH12

def accelerometer():
    print("ACCELEROMETER:", "accel:", accelerometer_sensor.acceleration(), "roll:", accelerometer_sensor.roll(), "pitch:", accelerometer_sensor.pitch(), "x/y/z:", accelerometer_sensor.x, accelerometer_sensor.y, accelerometer_sensor.z )

def activity_int_handler(pin_o):
    if pin_o():
        print('[Activity]')
        pycom.rgbled(0x00000A) # blue
    else:
        print('[Inactivity]')
        pycom.rgbled(0x0A0A00) # yellow

def activity_int_handler_none(pin_o):
    pass

def blink(color=0x0a0a0a, ct=5, on_ms=100, off_ms=100 ):
    while ct >= 0 :
        ct -= 1
        pycom.rgbled(color)
        time.sleep_ms(on_ms)
        pycom.rgbled(0x000000)
        time.sleep_ms(off_ms)

def wait(color=0x0a0a0a, hold_timeout_ms=3000):
    print(" - tap MCLR button to go to ultra low power mode (everything off)")
    print(" - hold MCLR button down for", round(hold_timeout_ms/1000,1), "sec to go to low power mode and wake from accelerometer")
    print("wait for button ...")
    ct = 0
    pressed_time_ms = 0
    dot = '.'
    while True:
        if pycoproc.button_pressed():
            if pressed_time_ms == 0:
                # the button just started to be pressed
                pressed_time_ms = time.ticks_ms()
                print("button pressed")
                pycom.rgbled(color)
                dot = '*'
            else:
                # the button is still being held down
                if time.ticks_ms() - pressed_time_ms > hold_timeout_ms:
                    pycom.rgbled(0)
                    dot = '_'
        else:
            if pressed_time_ms != 0:
                # the button was released
                print("button released")
                if time.ticks_ms() - pressed_time_ms > hold_timeout_ms:
                    return True
                else:
                    return False
        time.sleep(0.1)
        ct += 1
        if ct % 10 == 0:
            print(dot, end='')

def pretty_reset_cause():
    mrc = machine.reset_cause()
    print('reset_cause', mrc, end=' ')
    if mrc == machine.PWRON_RESET:
        print("PWRON_RESET")
        # plug in
        # press reset button on module
        # reset button on JTAG board
        # core dump
    elif mrc == machine.HARD_RESET:
        print("HARD_RESET")
    elif mrc == machine.WDT_RESET:
        print("WDT_RESET")
        # machine.reset()
    elif mrc == machine.DEEPSLEEP_RESET:
        print("DEEPSLEEP_RESET")
        # machine.deepsleep()
    elif mrc == machine.SOFT_RESET:
        print("SOFT_RESET")
        # Ctrl-D
    elif mrc == machine.BROWN_OUT_RESET:
        print("BROWN_OUT_RESET")

def pretty_wake_reason():
    mwr = machine.wake_reason()
    print("wake_reason", mwr, end=' ')
    if mwr[0] == machine.PWRON_WAKE:
        print("PWRON_WAKE")
        # reset button
    elif mwr[0] == machine.PIN_WAKE:
        print("PIN_WAKE")
    elif mwr[0] == machine.RTC_WAKE:
        print("RTC_WAKE")
        # from deepsleep
    elif mwr[0] == machine.ULP_WAKE:
        print("ULP_WAKE")


###############################################################
sleep_time_s = 300 # 5 min
pycom.heartbeat(False)
pycom.rgbled(0x0a0a0a) # white
import binascii
import machine
print(os.uname().sysname.lower() + '-' + binascii.hexlify(machine.unique_id()).decode("utf-8")[-4:], "pysense2")

pretty_wake_reason()
pretty_reset_cause()
print("pycoproc init")
pycoproc = Pycoproc()
print("battery {:.2f} V".format(pycoproc.read_battery_voltage()))

# init accelerometer
accelerometer_sensor = LIS2HH12()
# read accelerometer sensor values
accelerometer()
print("enable accelerometer interrupt")

# enable_activity_interrupt( [mG], [ms], callback)
# accelerometer_sensor.enable_activity_interrupt(8000, 200, activity_int_handler) # low sensitivty
# accelerometer_sensor.enable_activity_interrupt(2000, 200, activity_int_handler) # medium sensitivity
accelerometer_sensor.enable_activity_interrupt( 100, 200, activity_int_handler) # high sensitivity
# accelerometer_sensor.enable_activity_interrupt(63, 160, activity_int_handler) # ultra sensitivty

if wait(0x0A000A): # purple
    print("button was held")
    blink(0x000a00) # green
    print("enable pycom module to wake up from accelerometer interrupt")
    wake_pins = [Pin('P13', mode=Pin.IN, pull=Pin.PULL_DOWN)]
    machine.pin_sleep_wakeup(wake_pins, machine.WAKEUP_ANY_HIGH, True)

    print("put pycoproc to sleep and pycom module to deepsleep for", round(sleep_time_s/60,1), "minutes")
    pycoproc.setup_sleep(sleep_time_s)
    pycoproc.go_to_sleep(pycom_module_off=False, accelerometer_off=False, wake_interrupt=True)
    machine.deepsleep(sleep_time_s * 1000)
else:
    print("button was tapped")
    blink(0x100600) # orange
    print("put pycoproc to sleep and turn pycom module off for", round(sleep_time_s/60,1), "minutes")
    pycoproc.setup_sleep(sleep_time_s)
    pycoproc.go_to_sleep()

print("we never reach here!")
