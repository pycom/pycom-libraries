from machine import Pin
import time

__version__ = '1.0.0'

class Pysense:

    I2C_SLAVE_ADDR = const(8)

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

    PORTA_ADDR = const(0x00C)
    PORTC_ADDR = const(0x00E)

    WPUA_ADDR = const(0x20C)

    MEMORY_BANK_ADDR = const(0x620)

    PCON_ADDR = const(0x096)
    STATUS_ADDR = const(0x083)

class Pysense:

    def __init__(self, i2c=None, sda='P22', scl='P21'):
        if i2c is not None:
            self.i2c = i2c
        else:
            from machine import I2C
            self.i2c = I2C(0, mode=I2C.MASTER, pins=(sda, scl))
        self.reg = bytearray(6)
        scan_r = self.i2c.scan()
        if not scan_r or not I2C_SLAVE_ADDR in scan_r:
            raise Exception('Pysense board not detected')

        # init the ADC for the battery measurements
        self.poke_memory(ANSELC_ADDR, 1 << 2)
        self.poke_memory(ADCON0_ADDR, (0x06 << _ADCON0_CHS_POSN) | _ADCON0_ADON_MASK)
        self.poke_memory(ADCON1_ADDR, (0x06 << _ADCON1_ADCS_POSN))
        # enable the pull-up on RA3
        self.poke_memory(WPUA_ADDR, (1 << 3))

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

    def read_hw_version(self):
        self._send_cmd(CMD_HW_VER)
        d = self._read(2)
        return (d[1] << 8) + d[0]

    def read_fw_version(self):
        self._send_cmd(CMD_FW_VER)
        d = self._read(2)
        return (d[1] << 8) + d[0]

    def read_product_id(self):
        self._send_cmd(CMD_PROD_ID)
        d = self._read(2)
        return (d[1] << 8) + d[0]

    def peek_memory(self, addr):
        self._write(bytes([CMD_PEEK, addr & 0xFF, (addr >> 8) & 0xFF]))
        return self._read(1)[0]

    def poke_memory(self, addr, value):
        self._write(bytes([CMD_POKE, addr & 0xFF, (addr >> 8) & 0xFF, value & 0xFF]))

    def magic_write_read(self, addr, _and=0xFF, _or=0, _xor=0):
        self._write(bytes([CMD_MAGIC, addr & 0xFF, (addr >> 8) & 0xFF, _and & 0xFF, _or & 0xFF, _xor & 0xFF]))
        return self._read(1)[0]

    def toggle_bits_in_memory(self, addr, bits):
        self.magic_write_read(addr, _xor=bits)

    def mask_bits_in_memory(self, addr, mask):
        self.magic_write_read(addr, _and=mask)

    def set_bits_in_memory(self, addr, bits):
        self.magic_write_read(addr, _or=bits)

    def setup_sleep(self, time_s):
        self._write(bytes([CMD_SETUP_SLEEP, time_s & 0xFF, (time_s >> 8) & 0xFF, (time_s >> 16) & 0xFF]))

    def go_to_sleep(self):
        self.poke_memory(ADCON0_ADDR, 0)    # disable the ADC
        self.poke_memory(ANSELA_ADDR, ~(1 << 3))   # Don't touch RA3 so that button wake up works
        self.poke_memory(ANSELB_ADDR, 0xFF)
        self.poke_memory(ANSELC_ADDR, ~(1 << 7))
        self._write(bytes([CMD_GO_SLEEP]), wait=False)
        # kill the run pin
        Pin('P3', mode=Pin.OUT, value=0)

    def button_pressed(self):
        button = self.peek_memory(PORTA_ADDR) & (1 << 3)
        return not button

    def read_battery_voltage(self):
        self.set_bits_in_memory(ADCON0_ADDR, _ADCON0_GO_nDONE_MASK)
        time.sleep_us(50)
        while self.peek_memory(ADCON0_ADDR) & _ADCON0_GO_nDONE_MASK:
            time.sleep_us(100)
        adc_val = (self.peek_memory(ADRESH_ADDR) << 2) + (self.peek_memory(ADRESL_ADDR) >> 6)
        return (((adc_val * 3.3 * 280) / 1023) / 180) + 0.01    # add 10mV to compensate for the drop in the FET
