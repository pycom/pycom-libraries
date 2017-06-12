from machine import I2C
from machine import Pin
import machine
import time
import struct
import math

class Pytrack:

    I2C_SLAVE_ADDR = const(8)    # This one seems to be an unpopular addresss
    LIS2HH12_I2C_ADDR = const(30)   # both Pysense and Pytrack have the accelerometer onboard

    CMD_PEEK = const(0x0)
    CMD_POKE = const(0x01)
    CMD_MAGIC = const(0x02)
    CMD_HW_VER = const(0x10)
    CMD_FW_VER = const(0x11)
    CMD_PROD_ID = const(0x12)
    CMD_SETUP_SLEEP = const(0x20)
    CMD_GO_SLEEP = const(0x21)
    CMD_BAUD_CHANGE = const(0x30)
    CMD_DFU = const(0x31)

    REG_CMD = const(0)
    REG_ADDRL = const(1)
    REG_ADDRH = const(2)
    REG_AND = const(3)
    REG_OR = const(4)
    REG_XOR = const(5)

    ANSELA_ADDR = const(0x18C)
    ANSELB_ADDR = const(0x18D)
    ANSELC_ADDR = const(0x18E)

    ADCON0_ADDR = const(0x9D)
    ADCON1_ADDR = const(0x9E)

    _ADCON0_CHS_POSN = const(0x02)
    _ADCON0_ADON_MASK = const(0x01)
    _ADCON1_ADCS_POSN = const(0x04)
    _ADCON0_GO_nDONE_MASK = const(0x02)

    ADRESL_ADDR = const(0x09B)
    ADRESH_ADDR = const(0x09C)

    PORTC_ADDR = const(0x00E)

    WPUA_ADDR = const(0x20C)

    MEMORY_BANK_ADDR = const(0x620)

    def __init__(self, i2c=None, sda='P22', scl='P21'):
        if i2c is not None:
            self.i2c = i2c
        else:
            self.i2c = I2C(0, mode=I2C.MASTER, pins=(sda, scl))
        self.reg = bytearray(6)
        scan_r = self.i2c.scan()
        if not scan_r or LIS2HH12_I2C_ADDR not in scan_r or not I2C_SLAVE_ADDR in scan_r:
            raise Exception('Pytrack board not detected')

    def _write(self, data, wait=True):
        self.i2c.writeto(I2C_SLAVE_ADDR, data)
        if wait:
            self._wait()

    def _read(self, size):
        return self.i2c.readfrom(I2C_SLAVE_ADDR, size + 1)[1:(size + 1)]

    def _wait(self):
        time.sleep_us(100)
        while self.i2c.readfrom(I2C_SLAVE_ADDR, 1)[0] != 0xFF:
            time.sleep_us(100)

    def _send_cmd(self, cmd):
        self._write(bytes([cmd]))

    def setup_sleep(self, time_s):
        self._write(bytes([CMD_SETUP_SLEEP, time_s & 0xFF, (time_s >> 8) & 0xFF, (time_s >> 16) & 0xFF]))

    def go_to_sleep(self):
        self._write(bytes([CMD_GO_SLEEP]), wait=False)
        # kill the run pin
        Pin('P3', mode=Pin.OUT, value=0)
