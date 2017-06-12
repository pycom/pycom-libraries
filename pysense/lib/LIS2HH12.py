import math
import struct

class LIS2HH12:

    ACC_I2CADDR = const(30)

    PRODUCTID_REG = const(0x0F)
    CTRL1_REG = const(0x20)
    CTRL4_REG = const(0x23)
    ACC_X_L_REG = const(0x28)
    ACC_X_H_REG = const(0x29)
    ACC_Y_L_REG = const(0x2A)
    ACC_Y_H_REG = const(0x2B)
    ACC_Z_L_REG = const(0x2C)
    ACC_Z_H_REG = const(0x2D)

    def __init__(self, pysense=None, sda='P22', scl='P21'):
        if pysense is not None:
            self.i2c = pysense.i2c
        else:
            from machine import I2C
            self.i2c = I2C(0, mode=I2C.MASTER, pins=(sda, scl))

        self.reg = bytearray(1)

        self.x = 0
        self.y = 0
        self.z = 0

        whoami = self.i2c.readfrom_mem(ACC_I2CADDR , PRODUCTID_REG, 1)
        if (whoami[0] != 0x41):
            raise ValueError("Incorrect product ID")
        # enable acceleration readings
        self.i2c.readfrom_mem_into(ACC_I2CADDR , CTRL1_REG, self.reg)
        self.reg[0] &= ~0x70
        self.reg[0] |= 0x30
        self.i2c.writeto_mem(ACC_I2CADDR , CTRL1_REG, self.reg)
        # change the full-scale to 4g
        self.i2c.readfrom_mem_into(ACC_I2CADDR , CTRL4_REG, self.reg)
        self.reg[0] &= ~0b00110000
        self.reg[0] |= 0b00100000
        self.i2c.writeto_mem(ACC_I2CADDR , CTRL4_REG, self.reg)
        self.read()

    def read(self):
        x = self.i2c.readfrom_mem(ACC_I2CADDR , ACC_X_L_REG, 2)
        self.x = struct.unpack('<h', x)
        y = self.i2c.readfrom_mem(ACC_I2CADDR , ACC_Y_L_REG, 2)
        self.y = struct.unpack('<h', y)
        z = self.i2c.readfrom_mem(ACC_I2CADDR , ACC_Z_L_REG, 2)
        self.z = struct.unpack('<h', z)
        return (self.x[0], self.y[0], self.z[0])

    def roll(self):
        div = math.sqrt(math.pow(self.y[0], 2) + math.pow(self.z[0], 2))
        if div == 0:
            div = 0.01
        return (180 / 3.14154) * math.atan(self.x[0] / div)

    def pitch(self):
        if self.z[0] == 0:
            div = 1
        else:
            div = self.z[0]
        return (180 / 3.14154) * math.atan(math.sqrt(math.pow(self.x[0], 2) + math.pow(self.y[0], 2)) / div)

    def yaw(self):
        div = math.sqrt(math.pow(self.x[0], 2) + math.pow(self.z[0], 2))
        if div == 0:
            div = 0.01
        return (180 / 3.14154) * math.atan(self.y[0] / div)
