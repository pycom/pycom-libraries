import time

class LTR329ALS01:

    ALS_I2CADDR = const(0x29)
    ALS_CONTR_REG = const(0x80)
    ALS_MEAS_REG = const(0x85)
    ALS_DATA_CH0_LOW = const(0x8A)
    ALS_DATA_CH0_HIGH = const(0x8B)
    ALS_DATA_CH1_LOW = const(0x88)
    ALS_DATA_CH1_HIGH = const(0x89)
    ALS_GAIN_1X = const(0x01)
    ALS_GAIN_2X = const(0x05)
    ALS_GAIN_4X = const(0x09)
    ALS_GAIN_8X = const(0x0D)
    ALS_GAIN_48X = const(0x19)
    ALS_GAIN_96X = const(0x1D)
    ALS_INT_50 = const(0x01)
    ALS_INT_100 = const(0x00)
    ALS_INT_150 = const(0x04)
    ALS_INT_200 = const(0x02)
    ALS_INT_250 = const(0x05)
    ALS_INT_300 = const(0x06)
    ALS_INT_350 = const(0x07)
    ALS_INT_400 = const(0x03)
    ALS_RATE_50 = const(0x00)
    ALS_RATE_100 = const(0x01)
    ALS_RATE_200 = const(0x02)
    ALS_RATE_500 = const(0x03)
    ALS_RATE_1000 = const(0x04)
    ALS_RATE_2000 = const(0x05)

    def __init__(self, pysense=None, sda='P22', scl='P21', gain=ALS_GAIN_1X, integration=ALS_INT_100, rate=ALS_RATE_500):
        if pysense is not None:
            self.i2c = pysense.i2c
        else:
            from machine import I2C
            self.i2c = I2C(0, mode=I2C.MASTER, pins=(sda, scl))

        self.i2c.writeto_mem(ALS_I2CADDR, ALS_CONTR_REG, bytearray([gain]))
        meas = self._concat_hex(integration, rate)
        self.i2c.writeto_mem(ALS_I2CADDR, ALS_MEAS_REG, bytearray([meas]))
        time.sleep(0.01)

    def _concat_hex(self, a, b):
        sizeof_b = 0
        while((b >> sizeof_b) > 0):
            sizeof_b += 1
        sizeof_b += sizeof_b % 4
        return (a << sizeof_b) | b

    def lux(self):
        data0 = self.i2c.readfrom_mem(ALS_I2CADDR , ALS_DATA_CH1_LOW, 1)
        data1 = self.i2c.readfrom_mem(ALS_I2CADDR , ALS_DATA_CH1_HIGH, 1)
        data2 = self.i2c.readfrom_mem(ALS_I2CADDR , ALS_DATA_CH0_LOW, 1)
        data3 = self.i2c.readfrom_mem(ALS_I2CADDR , ALS_DATA_CH0_HIGH, 1)
        data_reg_CH1 = self._concat_hex(data1[0], data0[0])
        data_reg_CH0 = self._concat_hex(data2[0], data3[0])
        return(data_reg_CH0, data_reg_CH1)
