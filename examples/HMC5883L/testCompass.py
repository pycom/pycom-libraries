# execfile('testCompass.py')
import HMC5883L
import gc
import time
m = HMC5883L.HMC5883L()
while True:
	m.readAxes()
	m.heading()
	print(m)
	time.sleep_ms(1000)
	gc.collect()
