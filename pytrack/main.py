from pytrack import Pytrack
from L76GNSS import L76GNSS
from LIS2HH12 import LIS2HH12

py = Pytrack()
gps = L76GNSS(py)
acc = LIS2HH12(py)

gps.coords()
acc.read()
