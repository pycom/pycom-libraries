'''
HMC5883L 3 Axis Digital Compass
datascheet: https://cdn-shop.adafruit.com/datasheets/HMC5883L_3-Axis_Digital_Compass_IC.pdf
autor: Karol Bieniaszewski
c: 2017
The MIT License (MIT)
Copyright (c) 2017 Karol Bieniaszewski, liviuslivius at op dot pl
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
'''

from machine import I2C
from array import array
import math
import gc
import time

HMC5883L_sampling_mode_continous = bytes([0x00])
HMC5883L_sampling_mode_single    = bytes([0x01])
HMC5883L_sampling_mode_idle      = bytes([0x02])

HMC5883L_samples_1 = 0
HMC5883L_samples_2 = 32
HMC5883L_samples_4 = 64
HMC5883L_samples_8 = 96

HMC5883L_rate_00_75 = 0
HMC5883L_rate_01_50 = 4
HMC5883L_rate_03_00 = 8
HMC5883L_rate_07_50 = 12
HMC5883L_rate_15_00 = 16
HMC5883L_rate_75_00 = 20

HMC5883L_measurement_mode_bias_disabled = 0
HMC5883L_measurement_mode_bias_positive = 1
HMC5883L_measurement_mode_bias_negative = 2

HMC5883L_gauss_gain = {
	"0.88": [0, 0.73],
	"1.3":  [32, 0.92],
	"1.9":  [64, 1.22],
	"2.5":  [96, 1.52],
	"4.0":  [128, 2.27],
	"4.7":  [160, 2.56],
	"5.6":  [192, 3.03],
	"8.1":  [224, 4.35]
	}

def complement2toInt(value, len):
	if (value & (1 << len - 1)):
		value = value - (1<<len)
	return value

class HMC5883L():
		
	def __init__(self, busI2C=None, port=0, sensor_address=30, gauss="1.3", declinationDegrees=0, declinationMinutes=0):
		if busI2C==None:
			self.bus = I2C(port, I2C.MASTER, baudrate=100000) # max 400000 MR7 can change it
		else:
			self.bus = busI2C
		self.address = sensor_address
		self.setDeclination(declinationDegrees, declinationMinutes)
		self.headingDeg = None
		
		self.__data = bytearray([0]*6)
		self.x = 0
		self.y = 0
		self.z = 0
		self.__error = -4096
		self.wasError = 0
		
		self.samples = HMC5883L_samples_8
		self.rate = HMC5883L_rate_15_00
		self.bias = HMC5883L_measurement_mode_bias_disabled
		self.setRegA()
		
		self.gauss=gauss
		self.gauss_mask, self.gauss_scale=HMC5883L_gauss_gain[gauss]
		
		self.bus.writeto_mem(self.address, 0x01, bytes([self.gauss_mask]))
		self.setMode(HMC5883L_sampling_mode_continous)
		time.sleep_ms(67) #1/15 Hz
	
	def setDeclination(self, degrees, minutes):
		self.declDegrees = degrees
		self.declMinutes = minutes
		self.declination = (degrees + minutes / 60.0) * math.pi / 180.0	
	
	def setRegA(self):
		self.bus.writeto_mem(self.address, 0x02, bytes([self.bias | self.samples | self.rate]))	
		
	def setSamples(self, samples):
		self.samples = samples
		self.setRegA()
		
	def setRate(self, rate):
		self.rate = rate
		self.setRegA()	
		
	def setBias(self, bias):
		self.bias = bias
		self.setRegA()
	
	def setMode(self, mode):
		self.bus.writeto_mem(self.address, 0x02, mode) 
	
	def declination(self):
		return (self.declDegrees, self.declMinutes)

	def convert(self, data, offset):
		val = complement2toInt(data[offset] << 8 | data[offset+1], 16)
		if val == self.__error: return None
		return round(val * self.gauss_scale, 4)

	def readAxes(self):
		self.wasError = 0
		self.bus.readfrom_mem_into(self.address, 0x03, self.__data)
		#self.x = self.convert(self.__data, 0)
		self.x = self.__data[0] << 8 | self.__data[0+1]
		if (self.x & (1 << 16 - 1)):
			self.x-= (1<<16)
		if self.x == self.__error:
			self.x=None
			self.wasError = 1
		else:
			self.x=round(self.x * self.gauss_scale, 4)				

		#self.z = self.convert(self.__data, 2)
		self.z = self.__data[2] << 8 | self.__data[2+1]
		if (self.z & (1 << 16 - 1)):
			self.z-= (1<<16)
		if self.z == self.__error:
			self.z=None
			self.wasError = 1
		else:
			self.z=round(self.z * self.gauss_scale, 4)		

		#self.y = self.convert(self.__data, 4)
		self.y = self.__data[4] << 8 | self.__data[4+1]
		if (self.y & (1 << 16 - 1)):
			self.y-= (1<<16)
		if self.y == self.__error:
			self.y=None
			self.wasError = 1
		else:
			self.y=round(self.y * self.gauss_scale, 4)		
		
	def heading(self):
		'''
		1° to 2° compass heading accuracy
		first call self.readAxes()
		'''		
		headingRad = math.atan2(self.y, self.x)
		headingRad += self.declination
		
		# correct to range 0-360
		if headingRad < 0:
			headingRad += 2 * math.pi
		elif headingRad > 2 * math.pi:
			headingRad -= 2 * math.pi

		self.headingDeg = headingRad * 180 / math.pi

	def __str__(self):
		'''
		first call:
		self.readAxes()
		self.heading()
		'''
		return "X: " + str(self.x) + ", Y: " + str(self.y) + ", Z: " + str(self.z) + " - Heading: " + str(self.headingDeg) + ", Declination: " + str((self.declDegrees,self.declMinutes)) + "\n"
