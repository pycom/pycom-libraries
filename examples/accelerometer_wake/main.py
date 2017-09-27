from pytrack import Pytrack
#from pysense import Pysense
from LIS2HH12 import LIS2HH12
import pycom
import time

pycom.heartbeat(False)

py = Pytrack()
# py = Pysense()

# enable activity and also inactivity interrupts, using the default callback handler
py.setup_int_wake_up(True, True)

acc = LIS2HH12()
# enable the activity/inactivity interrupts
# set the accelereation threshold to 2000mG (2G) and the min duration to 200ms 
acc.enable_activity_interrupt(2000, 200)

# check if we were awaken due to activity
if acc.activity():
    pycom.rgbled(0xFF0000)
else:
    pycom.rgbled(0x00FF00)  # timer wake-up
time.sleep(0.1)

# go to sleep for 5 minutes maximum if no accelerometer interrupt happens
py.setup_sleep(300)
py.go_to_sleep()
