#!/usr/bin/env python
#
# Copyright (c) 2020, Pycom Limited.
#
# This software is licensed under the GNU GPL version 3 or any
# later version, with permitted additional terms. For more information
# see the Pycom Licence v1.0 document supplied with this file, or
# available at https://www.pycom.io/opensource/licensing
#

# See https://docs.pycom.io for more information regarding library specifics

from machine import Pin
from machine import I2C
import time
import pycom

__version__ = '0.0.2'

""" PIC MCU wakeup reason types """
WAKE_REASON_ACCELEROMETER = 1
WAKE_REASON_PUSH_BUTTON = 2
WAKE_REASON_TIMER = 4
WAKE_REASON_INT_PIN = 8

class Pycoproc:
    """ class for handling the interaction with PIC MCU """

    I2C_SLAVE_ADDR = const(8)

    PYSENSE = const(1)
    PYTRACK = const(2)
    PYSCAN = const(3)

    BOARD_TYPE_SET = (PYSENSE, PYTRACK, PYSCAN)

    CMD_PEEK = const(0x0)
    CMD_POKE = const(0x01)
    CMD_MAGIC = const(0x02)
    CMD_HW_VER = const(0x10)
    CMD_FW_VER = const(0x11)
    CMD_PROD_ID = const(0x12)
    CMD_SETUP_SLEEP = const(0x20)
    CMD_GO_SLEEP = const(0x21)
    CMD_CALIBRATE = const(0x22)
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

    IOCAP_ADDR = const(0x391)
    IOCAN_ADDR = const(0x392)

    INTCON_ADDR = const(0x0B)
    OPTION_REG_ADDR = const(0x95)

    _ADCON0_CHS_POSN = const(0x02)
    _ADCON0_ADON_MASK = const(0x01)
    _ADCON1_ADCS_POSN = const(0x04)
    _ADCON0_GO_nDONE_MASK = const(0x02)

    ADRESL_ADDR = const(0x09B)
    ADRESH_ADDR = const(0x09C)

    TRISC_ADDR = const(0x08E)

    PORTA_ADDR = const(0x00C)
    PORTC_ADDR = const(0x00E)

    WPUA_ADDR = const(0x20C)

    WAKE_REASON_ADDR = const(0x064C)
    MEMORY_BANK_ADDR = const(0x0620)

    PCON_ADDR = const(0x096)
    STATUS_ADDR = const(0x083)

    EXP_RTC_PERIOD = const(7000)

    def __init__(self, board_type, i2c=None, sda='P22', scl='P21'):
        if i2c is not None:
            self.i2c = i2c
        else:
            self.i2c = I2C(0, mode=I2C.MASTER, pins=(sda, scl))

        if board_type not in self.BOARD_TYPE_SET:
            raise Exception('Board type not in the set {}'.format(self.BOARD_TYPE_SET))

        self.sda = sda
        self.scl = scl
        self.board_type = board_type
        self.clk_cal_factor = 1
        self.reg = bytearray(6)
        self.wake_int = False
        self.wake_int_pin = False
        self.wake_int_pin_rising_edge = True

        # Make sure we are inserted into the
        # correct board and can talk to the PIC
        try:
            self.read_fw_version()
        except Exception as e:
            raise Exception('Board not detected: {}'.format(e))

        # init the ADC for the battery measurements
        self.poke_memory(ANSELC_ADDR, 1 << 2)
        self.poke_memory(ADCON0_ADDR, (0x06 << _ADCON0_CHS_POSN) | _ADCON0_ADON_MASK)
        self.poke_memory(ADCON1_ADDR, (0x06 << _ADCON1_ADCS_POSN))
        # enable the pull-up on RA3
        self.poke_memory(WPUA_ADDR, (1 << 3))
        # make RC5 an input
        self.set_bits_in_memory(TRISC_ADDR, 1 << 5)
        # set RC6 and RC7 as outputs and enable power to the sensors and the GPS
        self.mask_bits_in_memory(TRISC_ADDR, ~(1 << 6))
        self.mask_bits_in_memory(TRISC_ADDR, ~(1 << 7))

        if self.read_fw_version() < 6:
            raise ValueError('Firmware for Shield1 out of date')


    def _write(self, data, wait=True):
        self.i2c.writeto(I2C_SLAVE_ADDR, data)
        if wait:
            self._wait()

    def _read(self, size):
        return self.i2c.readfrom(I2C_SLAVE_ADDR, size + 1)[1:(size + 1)]

    def _wait(self):
        count = 0
        time.sleep_us(10)
        while self.i2c.readfrom(I2C_SLAVE_ADDR, 1)[0] != 0xFF:
            time.sleep_us(100)
            count += 1
            if (count > 500):  # timeout after 50ms
                raise Exception('Board timeout')

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

    def get_wake_reason(self):
        """ returns the wakeup reason, a value out of constants WAKE_REASON_* """
        return self.peek_memory(WAKE_REASON_ADDR)

    def get_sleep_remaining(self):
        """ returns the remaining time from sleep, as an interrupt (wakeup source) might have triggered """
        c3 = self.peek_memory(WAKE_REASON_ADDR + 3)
        c2 = self.peek_memory(WAKE_REASON_ADDR + 2)
        c1 = self.peek_memory(WAKE_REASON_ADDR + 1)
        time_device_s = (c3 << 16) + (c2 << 8) + c1
        # this time is from PIC internal oscilator, so it needs to be adjusted with the calibration value
        try:
            self.calibrate_rtc()
        except Exception:
            pass
        time_s = int((time_device_s / self.clk_cal_factor) + 0.5) # 0.5 used for round
        return time_s

    def setup_sleep(self, time_s):
        try:
            self.calibrate_rtc()
        except Exception:
            pass
        time_s = int((time_s * self.clk_cal_factor) + 0.5)  # round to the nearest integer
        if time_s >= 2**(8*3):
            time_s = 2**(8*3)-1
        self._write(bytes([CMD_SETUP_SLEEP, time_s & 0xFF, (time_s >> 8) & 0xFF, (time_s >> 16) & 0xFF]))

    def go_to_sleep(self, gps=True):
        # if we have a Pytrack then enable or disable back-up power to the GPS receiver
        if self.board_type == self.PYTRACK and gps:
            # disable GPS only if Pytrack
            self.set_bits_in_memory(PORTC_ADDR, 1 << 7)
        else:
            # Pysense or Pyscan or no GPS
            self.mask_bits_in_memory(PORTC_ADDR, ~(1 << 7))

        # disable the ADC
        self.poke_memory(ADCON0_ADDR, 0)

        if self.wake_int:
            # Don't touch RA3, RA5 or RC1 so that interrupt wake-up works
            self.poke_memory(ANSELA_ADDR, ~((1 << 3) | (1 << 5)))
            self.poke_memory(ANSELC_ADDR, ~((1 << 6) | (1 << 7) | (1 << 1)))
        else:
            # disable power to the accelerometer, and don't touch RA3 so that button wake-up works
            self.poke_memory(ANSELA_ADDR, ~(1 << 3))
            self.poke_memory(ANSELC_ADDR, ~(1 << 7))

        self.poke_memory(ANSELB_ADDR, 0xFF)

        # check if INT pin (PIC RC1), should be used for wakeup
        if self.wake_int_pin:
            if self.wake_int_pin_rising_edge:
                self.set_bits_in_memory(OPTION_REG_ADDR, 1 << 6) # rising edge of INT pin
            else:
                self.mask_bits_in_memory(OPTION_REG_ADDR, ~(1 << 6)) # falling edge of INT pin
            self.mask_bits_in_memory(ANSELC_ADDR, ~(1 << 1)) # disable analog function for RC1 pin
            self.set_bits_in_memory(TRISC_ADDR, 1 << 1) # make RC1 input pin
            self.mask_bits_in_memory(INTCON_ADDR, ~(1 << 1)) # clear INTF
            self.set_bits_in_memory(INTCON_ADDR, 1 << 4) # enable interrupt; set INTE)

        self._write(bytes([CMD_GO_SLEEP]), wait=False)
        # kill the run pin
        Pin('P3', mode=Pin.OUT, value=0)

    def calibrate_rtc(self):
        # the 1.024 factor is because the PIC LF operates at 31 KHz
        # WDT has a frequency divider to generate 1 ms
        # and then there is a binary prescaler, e.g., 1, 2, 4 ... 512, 1024 ms
        # hence the need for the constant
        self._write(bytes([CMD_CALIBRATE]), wait=False)
        self.i2c.deinit()
        Pin('P21', mode=Pin.IN)
        pulses = pycom.pulses_get('P21', 100)
        self.i2c.init(mode=I2C.MASTER, pins=(self.sda, self.scl))
        idx = 0
        for i in range(len(pulses)):
            if pulses[i][1] > EXP_RTC_PERIOD:
                idx = i
                break
        try:
            period = pulses[idx][1] - pulses[(idx - 1)][1]
        except:
            period = 0
        if period > 0:
            self.clk_cal_factor = (EXP_RTC_PERIOD / period) * (1000 / 1024)
        if self.clk_cal_factor > 1.25 or self.clk_cal_factor < 0.75:
            self.clk_cal_factor = 1

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

    def setup_int_wake_up(self, rising, falling):
        """ rising is for activity detection, falling for inactivity """
        wake_int = False
        if rising:
            self.set_bits_in_memory(IOCAP_ADDR, 1 << 5)
            wake_int = True
        else:
            self.mask_bits_in_memory(IOCAP_ADDR, ~(1 << 5))

        if falling:
            self.set_bits_in_memory(IOCAN_ADDR, 1 << 5)
            wake_int = True
        else:
            self.mask_bits_in_memory(IOCAN_ADDR, ~(1 << 5))
        self.wake_int = wake_int

    def setup_int_pin_wake_up(self, rising_edge = True):
        """ allows wakeup to be made by the INT pin (PIC -RC1) """
        self.wake_int_pin = True
        self.wake_int_pin_rising_edge = rising_edge
