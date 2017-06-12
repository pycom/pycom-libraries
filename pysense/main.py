from pysense import Pysense
from LIS2HH12 import LIS2HH12
from SI7006A20 import SI7006A20
from LTR329ALS01 import LTR329ALS01
from MPL3115A2 import MPL3115A2

py = Pysense()
pressure = MPL3115A2(py)
tempHum = SI7006A20(py)
ambientLight = LTR329ALS01(py)
acc = LIS2HH12(py)
