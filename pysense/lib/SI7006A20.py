import time
from machine import I2C

class SI7006A20:
    SI7006A20_I2C_ADDR = const(0x40)
    TEMP_NOHOLDMASTER = const(0xF3)
    HUMD_NOHOLDMASTER = const(0xF5)

    def __init__(self, pysense = None, sda = 'P22', scl = 'P21'):
        if pysense is not None:
            self.i2c = pysense.i2c
        else:
            self.i2c = I2C(0, mode=I2C.MASTER, pins=(sda, scl))

    def _getWord(self, high, low):
        return ((high & 0xFF) << 8) + (low & 0xFF)

    def temperature(self):
        self.i2c.writeto(SI7006A20_I2C_ADDR, bytearray([0xF3]))
        time.sleep(0.5)
        data = self.i2c.readfrom(SI7006A20_I2C_ADDR, 2)
        data = self._getWord(data[0], data[1])
        temp = ((175.72 * data) / 65536.0) - 46.85
        return temp

    def humidity(self):
        self.i2c.writeto(SI7006A20_I2C_ADDR, bytearray([0xF5]))
        time.sleep(0.5)
        data = self.i2c.readfrom(SI7006A20_I2C_ADDR, 2)
        data = self._getWord(data[0], data[1])
        humidity = ((125.0 * data) / 65536.0) - 6.0
        return humidity
