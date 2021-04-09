### Library for using Sparkfun Serial 7-Segment ###
### Made by Joachim Kristensen 2017, https://www.hackster.io/lokefar
### Git: https://github.com/lokefar
### using the Sparkfun Tutorial for reference/beginning
### https://learn.sparkfun.com/tutorials/using-the-serial-7-segment-display#example-1-serial-uart ###
### Special commands: https://github.com/sparkfun/Serial7SegmentDisplay/wiki/Special-Commands ###

### Suggestion for improvement:
### - Change decimal actions to be controlled via a bitwise operator so it is possible to have both
### colon, decimal points and apostrophe on at the same time


### Code to use in main.py
### import serial7segment
### serial7segment.SERIAL7SEGMENT(uart, 'clearDisplay') <-- I recommend to clearDisplay before writing new stuff
### serial7segment.SERIAL7SEGMENT(uart, '1234') <-- Most basic
### serial7segment.SERIAL7SEGMENT(uart, '1234', 5, 1, 50) <-- turns on the colon, moves the cursor places to 1 (string starts at 2)
### and sets the brightness at half (brightness is at the moment inverse, so 1 is brightest and 100 is darkest)


#Clear display
CLEAR_DISPLAY = 0x76

#Decimal control
DECIMAL_CONTROL = 0x77

#Cursor control
CURSOR_CONTROL = 0x79

#Brightness control
BRIGHTNESS = 0x7A

#Digit 1 control
DIGIT_1 = 0x00

#Digit 2 control
DIGIT_2 = 0x01

#Digit 3 control
DIGIT_3 = 0x02

#Digit 4 control
DIGIT_4 = 0x03

#Baud rate config
BAUD_RATE = 0x7F

#Decimal point place
#Place 1
DECIMAL_1 = 0x1 

#Place 2
DECIMAL_2 = 0x2

#Place 3
DECIMAL_3 = 0x4

#Place 4
DECIMAL_4 = 0x8

#Colon
DECIMAL_COLON = 0x10

class SERIAL7SEGMENT:
	def __init__(self, uart, text, decimal=None, offset=None, pwm=None):
		self.uart = uart
		self.text = text
		self.decimal = decimal
		self.offset = offset
		self.pwm = pwm
		if self.text == 'clearDisplay':
			self.clearDisplay(self.text)
		else:
			self.decimalPoint(self.decimal)
			self.offsetCursor(self.offset)
			self.writeNumber(self.text)

	def clearDisplay(self, text):
		self.uart.write(bytes([CLEAR_DISPLAY]))
		self.uart.write(bytes([DECIMAL_CONTROL, 0x0]))

	def decimalPoint(self, decimal):
		if decimal == 1:
			self.uart.write(bytes([DECIMAL_CONTROL, DECIMAL_1]))
		elif decimal == 2:
			self.uart.write(bytes([DECIMAL_CONTROL, DECIMAL_2]))
		elif decimal == 3:
			self.uart.write(bytes([DECIMAL_CONTROL, DECIMAL_3]))
		elif decimal == 4:
			self.uart.write(bytes([DECIMAL_CONTROL, DECIMAL_4]))
		elif decimal == 5:
			self.uart.write(bytes([DECIMAL_CONTROL, DECIMAL_COLON]))

	def offsetCursor(self, offset):
		if offset == 1:
			self.uart.write(bytes([CURSOR_CONTROL, DIGIT_1]))
		elif offset == 2:
			self.uart.write(bytes([CURSOR_CONTROL, DIGIT_2]))
		elif offset == 3:
			self.uart.write(bytes([CURSOR_CONTROL, DIGIT_3]))
		elif offset == 4:
			self.uart.write(bytes([CURSOR_CONTROL, DIGIT_4]))
	
	def pwmPower(self, pwm):
		if pwm != None:
			self.uart.write(bytes([BRIGHTNESS, DIGIT_4]))

	def writeNumber(self, text):
		self.uart.write(text)
		return self.text

