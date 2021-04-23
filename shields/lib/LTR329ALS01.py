#!/usr/bin/env python
#
# Copyright (c) 2020, Pycom Limited.
#
# This software is licensed under the GNU GPL version 3 or any
# later version, with permitted additional terms. For more information
# see the Pycom Licence v1.0 document supplied with this file, or
# available at https://www.pycom.io/opensource/licensing
#

import time
from machine import I2C

class LTR329ALS01:
    ALS_I2CADDR = const(0x29) # The device's I2C address

    ALS_CONTR_REG = const(0x80)
    ALS_MEAS_RATE_REG = const(0x85)

    ALS_DATA_CH1_LOW = const(0x88)
    ALS_DATA_CH1_HIGH = const(0x89)
    ALS_DATA_CH0_LOW = const(0x8A)
    ALS_DATA_CH0_HIGH = const(0x8B)

    ALS_GAIN_1X = const(0x00)
    ALS_GAIN_2X = const(0x01)
    ALS_GAIN_4X = const(0x02)
    ALS_GAIN_8X = const(0x03)
    ALS_GAIN_48X = const(0x06)
    ALS_GAIN_96X = const(0x07)
    ALS_GAIN_VALUES = {
        ALS_GAIN_1X: 1,
        ALS_GAIN_2X: 2,
        ALS_GAIN_4X: 4,
        ALS_GAIN_8X: 8,
        ALS_GAIN_48X: 48,
        ALS_GAIN_96X: 96
    }

    ALS_INT_50 = const(0x01)
    ALS_INT_100 = const(0x00)
    ALS_INT_150 = const(0x04)
    ALS_INT_200 = const(0x02)
    ALS_INT_250 = const(0x05)
    ALS_INT_300 = const(0x06)
    ALS_INT_350 = const(0x07)
    ALS_INT_400 = const(0x03)
    ALS_INT_VALUES = {
        ALS_INT_50: 0.5,
        ALS_INT_100: 1,
        ALS_INT_150: 1.5,
        ALS_INT_200: 2,
        ALS_INT_250: 2.5,
        ALS_INT_300: 3,
        ALS_INT_350: 3.5,
        ALS_INT_400: 4
    }

    ALS_RATE_50 = const(0x00)
    ALS_RATE_100 = const(0x01)
    ALS_RATE_200 = const(0x02)
    ALS_RATE_500 = const(0x03)
    ALS_RATE_1000 = const(0x04)
    ALS_RATE_2000 = const(0x05)

    def __init__(self, pysense = None, sda = 'P22', scl = 'P21', gain = ALS_GAIN_1X, integration = ALS_INT_100, rate = ALS_RATE_500):
        if pysense is not None:
            self.i2c = pysense.i2c
        else:
            self.i2c = I2C(0, mode=I2C.MASTER, pins=(sda, scl))

        self.gain = gain
        self.integration = integration

        contr = self._getContr(gain)
        self.i2c.writeto_mem(ALS_I2CADDR, ALS_CONTR_REG, bytearray([contr]))

        measrate = self._getMeasRate(integration, rate)
        self.i2c.writeto_mem(ALS_I2CADDR, ALS_MEAS_RATE_REG, bytearray([measrate]))

        time.sleep(0.01)

    def _getContr(self, gain):
        return ((gain & 0x07) << 2) + 0x01

    def _getMeasRate(self, integration, rate):
        return ((integration & 0x07) << 3) + (rate & 0x07)

    def _getWord(self, high, low):
        return ((high & 0xFF) << 8) + (low & 0xFF)

    def light(self):
        ch1low = self.i2c.readfrom_mem(ALS_I2CADDR , ALS_DATA_CH1_LOW, 1)
        ch1high = self.i2c.readfrom_mem(ALS_I2CADDR , ALS_DATA_CH1_HIGH, 1)
        data1 = int(self._getWord(ch1high[0], ch1low[0]))

        ch0low = self.i2c.readfrom_mem(ALS_I2CADDR , ALS_DATA_CH0_LOW, 1)
        ch0high = self.i2c.readfrom_mem(ALS_I2CADDR , ALS_DATA_CH0_HIGH, 1)
        data0 = int(self._getWord(ch0high[0], ch0low[0]))

        return (data0, data1)

    def lux(self):
        # Calculate Lux value from formular in Appendix A of the datasheet
        light_level = self.light()
        if light_level[0]+light_level[1] > 0:
            ratio = light_level[1]/(light_level[0]+light_level[1])
            if ratio < 0.45:
                return (1.7743 * light_level[0] + 1.1059 * light_level[1]) / self.ALS_GAIN_VALUES[self.gain] / self.ALS_INT_VALUES[self.integration]
            elif ratio < 0.64 and ratio >= 0.45:
                return (4.2785 * light_level[0] - 1.9548 * light_level[1]) / self.ALS_GAIN_VALUES[self.gain] / self.ALS_INT_VALUES[self.integration]
            elif ratio < 0.85 and ratio >= 0.64:
                return (0.5926 * light_level[0] + 0.1185 * light_level[1]) / self.ALS_GAIN_VALUES[self.gain] / self.ALS_INT_VALUES[self.integration]
            else:
                return 0
        else:
            return 0
