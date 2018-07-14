# See https://docs.pycom.io for more information regarding library specifics

from pytrack import Pytrack
from L76GNSS import L76GNSS
from LIS2HH12 import LIS2HH12

py = Pytrack()

l76 = L76GNSS(py, timeout=120) # GSP timeout set to 120 seconds
li = LIS2HH12(py)

print(li.acceleration())
print(li.roll())
print(li.pitch())
print(li.yaw())

print(l76.rmc())
