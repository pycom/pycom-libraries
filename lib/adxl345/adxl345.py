### This is an I2C driver for the Adafruit ADXL345 Accelerometer.
### Made by Joachim Kristensen 2017, https://www.hackster.io/lokefar
### Git: https://github.com/lokefar
### Inspired by https://github.com/pimoroni/adxl345-python
### At the moment it is possible to set the data range going from 2G to 16G
### Optimizations that could be done:
### - Write the binaries for the other output data rates
### - Write a calibration part
### - Make it possible to call the initiate the changes to data range and
### bandwidth from main program

### Code do use in main.py
### import adxl345
### data = adxl345.ADXL345(i2c)
### axes = data.getAxes(True)  <-- If you want in G, else False for acc



#The address of the ADXL345 given in the datasheet
ADXL345_ADDR = 0x53


#The bytes for making the ADXL345 send at 100Hz output data rate
BW_RATE_100HZ = 0x0B

#The address for making changes to POWER_CTL
POWER_CTL = 0x2D 
#The byte "code" for starting the measurements
MEASURE = 0x08

#The address for changing the DATA_FORMAT. This is used together with the ranges
DATA_FORMAT = 0x31

#The address where the measurement data starts from. Each axis has two bytes for the given value
AXES_DATA = 0x32

#The address for accessing and setting the bandwidth rate
BW_RATE = 0x2C

#Decide the range of measurements ie the precision. Possible options
#2G
RANGE_2G = 0x08
#4G
RANGE_4G = 0x09
#8G
RANGE_8G = 0x0A
#16G
RANGE_16G = 0x0F

SCALE_MULTIPLIER = 0.004

#Standard gravity constant for going from G-force to m/s^2
EARTH_GRAVITY_MS2 = 9.80665



class ADXL345:

	def __init__(self, i2c):
		self.i2c = i2c
		self.addr = ADXL345_ADDR
		self.setBandwidthRate(BW_RATE_100HZ)
		self.setRange(RANGE_2G)
		self.enableMeasurement()

	def enableMeasurement(self):
		self.i2c.writeto_mem(self.addr, POWER_CTL, bytes([MEASURE]))
		
	def setBandwidthRate(self, rate_flag):
		self.i2c.writeto_mem(self.addr, BW_RATE, bytes([rate_flag]))

	def setRange(self, range_flag):
		self.i2c.writeto_mem(self.addr, DATA_FORMAT, bytes([range_flag]))

	def getAxes(self, gforce = False):
		bytes = self.i2c.readfrom_mem(self.addr, AXES_DATA, 6)
		x = bytes[0] | (bytes[1] << 8)
		if(x & (1 << 16 - 1)):
			x = x - (1<<16)

		y = bytes[2] | (bytes[3] << 8)
		if(y & (1 << 16 - 1)):
			y = y - (1<<16)

		z = bytes[4] | (bytes[5] << 8 )
		if(z & (1 << 16 - 1)):
			z = z - (1<<16)

		x = x * SCALE_MULTIPLIER
		y = y * SCALE_MULTIPLIER
		z = z * SCALE_MULTIPLIER

		if gforce == False: 
			x = x * EARTH_GRAVITY_MS2
			y = y * EARTH_GRAVITY_MS2
			z = z * EARTH_GRAVITY_MS2

		x = round(x,4)
		y = round(y,4)
		z = round(z,4)

		return {"x": x, "y": y, "z": z}