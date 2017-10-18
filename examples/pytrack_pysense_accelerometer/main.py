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
