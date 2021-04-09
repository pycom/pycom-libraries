### Textstar display ###
### Inspired by http://jeremyblythe.blogspot.dk/2012/07/raspberry-pi-with-textstar-serial-lcd.html ###
### Made by Joachim Kristensen 2017, https://www.hackster.io/lokefar
### Git: https://github.com/lokefar
### Ideas for optimization:
### - Set cursor starting point
### - Make graphs/special characters

### Code to use in main program
### import textstar
### textstar.TEXTSTAR(uart, 'clearDisplay') <-- I recommend always clearing before writing new string
### textstar.TEXTSTAR(uart, 'MyString')

#Adresse for clearing display
CLEARDISPLAY = chr(12)


class TEXTSTAR:
	def __init__(self, uart, text):
		self.uart = uart
		self.text = text
		if self.text == 'clearDisplay':
			self.uart.write(CLEARDISPLAY)
		else:
			self.writeText(self.text)

	def writeText(self, text):
		self.uart.write(text)