import time

class MPL3115A2exception(Exception):
    pass

class MPL3115A2:

    MPL3115_I2CADDR             = const(0x60)
    MPL3115_STATUS              = const(0x00)
    MPL3115_PRESSURE_DATA_MSB   = const(0x01)
    MPL3115_PRESSURE_DATA_CSB   = const(0x02)
    MPL3115_PRESSURE_DATA_LSB   = const(0x03)
    MPL3115_TEMP_DATA_MSB       = const(0x04)
    MPL3115_TEMP_DATA_LSB       = const(0x05)
    MPL3115_DR_STATUS           = const(0x06)
    MPL3115_DELTA_DATA          = const(0x07)
    MPL3115_WHO_AM_I            = const(0x0c)
    MPL3115_FIFO_STATUS         = const(0x0d)
    MPL3115_FIFO_DATA           = const(0x0e)
    MPL3115_FIFO_SETUP          = const(0x0e)
    MPL3115_TIME_DELAY          = const(0x10)
    MPL3115_SYS_MODE            = const(0x11)
    MPL3115_INT_SORCE           = const(0x12)
    MPL3115_PT_DATA_CFG         = const(0x13)
    MPL3115_BAR_IN_MSB          = const(0x14)
    MPL3115_P_ARLARM_MSB        = const(0x16)
    MPL3115_T_ARLARM            = const(0x18)
    MPL3115_P_ARLARM_WND_MSB    = const(0x19)
    MPL3115_T_ARLARM_WND        = const(0x1b)
    MPL3115_P_MIN_DATA          = const(0x1c)
    MPL3115_T_MIN_DATA          = const(0x1f)
    MPL3115_P_MAX_DATA          = const(0x21)
    MPL3115_T_MAX_DATA          = const(0x24)
    MPL3115_CTRL_REG1           = const(0x26)
    MPL3115_CTRL_REG2           = const(0x27)
    MPL3115_CTRL_REG3           = const(0x28)
    MPL3115_CTRL_REG4           = const(0x29)
    MPL3115_CTRL_REG5           = const(0x2a)
    MPL3115_OFFSET_P            = const(0x2b)
    MPL3115_OFFSET_T            = const(0x2c)
    MPL3115_OFFSET_H            = const(0x2d)
    ALTITUDE		            = const(0)
    PRESSURE		            = const(1)

    def __init__(self, pysense=None, sda='P22', scl='P21'):
        if pysense is not None:
            self.i2c = pysense.i2c
        else:
            from machine import I2C
            self.i2c = I2C(0, mode=I2C.MASTER, pins=(sda, scl))

        self.STA_reg = bytearray(1)

        self.i2c.writeto_mem(MPL3115_I2CADDR, MPL3115_CTRL_REG1, bytes([0xB8]))
        self.i2c.writeto_mem(MPL3115_I2CADDR, MPL3115_PT_DATA_CFG, bytes([0x07]))
        self.i2c.writeto_mem(MPL3115_I2CADDR, MPL3115_CTRL_REG1, bytes([0xB9]))

        if self._read_status():
            pass
        else:
            raise MPL3115A2exception("Error with MPL3115A2")

    def _read_status(self):
        while True:

            self.i2c.readfrom_mem_into(MPL3115_I2CADDR, MPL3115_STATUS, self.STA_reg)

            if(self.STA_reg[0] == 0):
                time.sleep(0.01)
                pass
            elif(self.STA_reg[0] & 0x04) == 4:
                return True
            else:
                return False

    def _fixed_decimal(self, frac_value):
        fixed_decimal = 0

        for x in range(2,len(bin(frac_value))):
            fixed_decimal += int(bin(frac_value)[x])*(2**(-(x-1)))

        return fixed_decimal

    def alt(self):
        OUT_P_MSB = self.i2c.readfrom_mem(MPL3115_I2CADDR, MPL3115_PRESSURE_DATA_MSB,1)
        OUT_P_CSB = self.i2c.readfrom_mem(MPL3115_I2CADDR, MPL3115_PRESSURE_DATA_CSB,1)
        OUT_P_LSB = self.i2c.readfrom_mem(MPL3115_I2CADDR, MPL3115_PRESSURE_DATA_LSB,1)
        OUT_P_ALL = self.i2c.readfrom_mem(MPL3115_I2CADDR, MPL3115_PRESSURE_DATA_MSB,5)

        pres_frac = OUT_P_LSB[0] >> 4
        pres_int = (OUT_P_MSB[0] << 8)|(OUT_P_CSB[0])

        if (pres_int & (1 << (16 - 1))) != 0: # if sign bit is set e.g., 8bit: 128-255
            pres_int = pres_int - (1 << 16)

        pres_frac = self._fixed_decimal(pres_frac)

        return(float(str(pres_int)+str(pres_frac)[1:]))

    def temp(self):
        OUT_T_MSB = self.i2c.readfrom_mem(MPL3115_I2CADDR, MPL3115_TEMP_DATA_MSB,1)
        OUT_T_LSB = self.i2c.readfrom_mem(MPL3115_I2CADDR, MPL3115_TEMP_DATA_LSB,1)

        temp_frac = OUT_T_LSB[0] >> 4

        temp_int = OUT_T_MSB[0]

        if (temp_int & (1 << (8 - 1))) != 0: # if sign bit is set e.g., 8bit: 128-255
            temp_int = temp_int - (1 << 8)

        temp_frac = self._fixed_decimal(temp_frac)

        return(float(str(temp_int)+str(temp_frac)[1:]))
