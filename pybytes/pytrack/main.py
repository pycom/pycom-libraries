import machine
import math
import network
import os
import time
import utime
from machine import RTC
from machine import SD
from machine import Timer
from L76GNSS import L76GNSS
from pytrack import Pytrack
from LIS2HH12 import LIS2HH12
# setup as a station

import gc

time.sleep(2)
gc.enable()

# setup rtc
rtc = machine.RTC()
rtc.ntp_sync("pool.ntp.org")
utime.sleep_ms(750)
print('\nRTC Set from NTP to UTC:', rtc.now())
utime.timezone(7200)
print('Adjusted from UTC to EST timezone', utime.localtime(), '\n')
py = Pytrack()
l76 = L76GNSS(py, timeout=30)
chrono = Timer.Chrono()
chrono.start()
li = LIS2HH12(py)
#sd = SD()
#os.mount(sd, '/sd')
#f = open('/sd/gps-record.txt', 'w')
while (pybytes):
    coord = l76.coordinates()
    #f.write("{} - {}\n".format(coord, rtc.now()))
    print('Sending data')
    pybytes.send_virtual_pin_value(True, 1, coord)
    pybytes.send_virtual_pin_value(True, 2, li.acceleration())
    time.sleep(10)
