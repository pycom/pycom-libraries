import math
import time
import struct
from machine import Pin


FULL_SCALE_2G = const(0)
FULL_SCALE_4G = const(2)
FULL_SCALE_8G = const(3)

ODR_POWER_DOWN = const(0)
ODR_10_HZ = const(1)
ODR_50_HZ = const(2)
ODR_100_HZ = const(3)
ODR_200_HZ = const(4)
ODR_400_HZ = const(5)
ODR_800_HZ = const(6)

ACC_G_DIV = 1000 * 65536

class LIS2HH12:

    ACC_I2CADDR = const(30)

    PRODUCTID_REG = const(0x0F)
    CTRL1_REG = const(0x20)
    CTRL2_REG = const(0x21)
    CTRL3_REG = const(0x22)
    CTRL4_REG = const(0x23)
    CTRL5_REG = const(0x24)
    ACC_X_L_REG = const(0x28)
    ACC_X_H_REG = const(0x29)
    ACC_Y_L_REG = const(0x2A)
    ACC_Y_H_REG = const(0x2B)
    ACC_Z_L_REG = const(0x2C)
    ACC_Z_H_REG = const(0x2D)
    ACT_THS = const(0x1E)
    ACT_DUR = const(0x1F)

    def __init__(self, pysense = None, sda = 'P22', scl = 'P21'):
        if pysense is not None:
            self.i2c = pysense.i2c
        else:
            from machine import I2C
            self.i2c = I2C(0, mode=I2C.MASTER, pins=(sda, scl))

        self.reg = bytearray(1)
        self.odr = 0
        self.full_scale = 0
        self.x = 0
        self.y = 0
        self.z = 0
        self.int_pin = None
        self.act_dur = 0
        self.debounced = False

        self.scales = {FULL_SCALE_2G: 4000, FULL_SCALE_4G: 8000, FULL_SCALE_8G: 16000}
        self.odrs = [0, 10, 50, 100, 200, 400, 800]

        whoami = self.i2c.readfrom_mem(ACC_I2CADDR , PRODUCTID_REG, 1)
        if (whoami[0] != 0x41):
            raise ValueError("LIS2HH12 not found")

        # enable acceleration readings at 50Hz
        self.set_odr(ODR_50_HZ)

        # change the full-scale to 4g
        self.set_full_scale(FULL_SCALE_4G)

        # set the interrupt pin as active low and open drain
        self.i2c.readfrom_mem_into(ACC_I2CADDR , CTRL5_REG, self.reg)
        self.reg[0] |= 0b00000011
        self.i2c.writeto_mem(ACC_I2CADDR , CTRL5_REG, self.reg)

        # make a first read
        self.acceleration()

    def acceleration(self):
        x = self.i2c.readfrom_mem(ACC_I2CADDR , ACC_X_L_REG, 2)
        self.x = struct.unpack('<h', x)
        y = self.i2c.readfrom_mem(ACC_I2CADDR , ACC_Y_L_REG, 2)
        self.y = struct.unpack('<h', y)
        z = self.i2c.readfrom_mem(ACC_I2CADDR , ACC_Z_L_REG, 2)
        self.z = struct.unpack('<h', z)
        _mult = self.scales[self.full_scale] / ACC_G_DIV
        return (self.x[0] * _mult, self.y[0] * _mult, self.z[0] * _mult)

    def roll(self):
        x,y,z = self.acceleration()
        rad = math.atan2(-x, z)
        return (180 / math.pi) * rad

    def pitch(self):
        x,y,z = self.acceleration()
        rad = -math.atan2(y, (math.sqrt(x*x + z*z)))
        return (180 / math.pi) * rad

    def set_full_scale(self, scale):
        self.i2c.readfrom_mem_into(ACC_I2CADDR , CTRL4_REG, self.reg)
        self.reg[0] &= ~0b00110000
        self.reg[0] |= (scale & 3) << 4
        self.i2c.writeto_mem(ACC_I2CADDR , CTRL4_REG, self.reg)
        self.full_scale = scale

    def set_odr(self, odr):
        self.i2c.readfrom_mem_into(ACC_I2CADDR , CTRL1_REG, self.reg)
        self.reg[0] &= ~0b01110000
        self.reg[0] |= (odr & 7) << 4
        self.i2c.writeto_mem(ACC_I2CADDR , CTRL1_REG, self.reg)
        self.odr = odr

    def enable_activity_interrupt(self, threshold, duration, handler=None):
        # Threshold is in mg, duration is ms
        self.act_dur = duration

        _ths = int((threshold * self.scales[self.full_scale]) / 2000 / 128) & 0x7F
        _dur = int((duration * self.odrs[self.odr]) / 1000 / 8)

        self.i2c.writeto_mem(ACC_I2CADDR , ACT_THS, _ths)
        self.i2c.writeto_mem(ACC_I2CADDR , ACT_DUR, _dur)

        # enable the activity/inactivity interrupt
        self.i2c.readfrom_mem_into(ACC_I2CADDR , CTRL3_REG, self.reg)
        self.reg[0] |= 0b00100000
        self.i2c.writeto_mem(ACC_I2CADDR , CTRL3_REG, self.reg)

        self._user_handler = handler
        self.int_pin = Pin('P13', mode=Pin.IN)
        self.int_pin.callback(trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, handler=self._int_handler)

    def activity(self):
        if not self.debounced:
            time.sleep_ms(self.act_dur)
            self.debounced = True
        if self.int_pin():
            return True
        return False

    def _int_handler(self, pin_o):
        if self._user_handler is not None:
            self._user_handler(pin_o)
        else:
            if pin_o():
                print('Activity interrupt')
            else:
                print('Inactivity interrupt')
