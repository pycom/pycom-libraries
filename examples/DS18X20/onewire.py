#!/usr/bin/env python3

"""
OneWire library for MicroPython
"""

import time
import machine

class OneWire:
    CMD_SEARCHROM = const(0xf0)
    CMD_READROM = const(0x33)
    CMD_MATCHROM = const(0x55)
    CMD_SKIPROM = const(0xcc)

    def __init__(self, pin):
        self.pin = pin
        self.pin.init(pin.OPEN_DRAIN, pin.PULL_UP)
        self.disable_irq = machine.disable_irq
        self.enable_irq = machine.enable_irq
        self.crctab1 = (b"\x00\x5E\xBC\xE2\x61\x3F\xDD\x83"
                        b"\xC2\x9C\x7E\x20\xA3\xFD\x1F\x41")
        self.crctab2 = (b"\x00\x9D\x23\xBE\x46\xDB\x65\xF8"
                        b"\x8C\x11\xAF\x32\xCA\x57\xE9\x74")


    def reset(self):
        """
        Perform the onewire reset function.
        Returns True if a device asserted a presence pulse, False otherwise.
        """
        sleep_us = time.sleep_us
        pin = self.pin

        pin(0)
        sleep_us(480)
        i = self.disable_irq()
        pin(1)
        sleep_us(60)
        status = not pin()
        self.enable_irq(i)
        sleep_us(420)
        return status

    def read_bit(self):
        sleep_us = time.sleep_us
        pin = self.pin

        pin(1) # half of the devices don't match CRC without this line
        i = self.disable_irq()
        pin(0)
        # skip sleep_us(1) here, results in a 2 us pulse.
        pin(1)
        sleep_us(5) # 8 us delay in total
        value = pin()
        self.enable_irq(i)
        sleep_us(40)
        return value

    def read_byte(self):
        value = 0
        for i in range(8):
            value |= self.read_bit() << i
        return value

    def read_bytes(self, count):
        buf = bytearray(count)
        for i in range(count):
            buf[i] = self.read_byte()
        return buf

    def write_bit(self, value):
        sleep_us = time.sleep_us
        pin = self.pin

        i = self.disable_irq()
        pin(0)
        sleep_us(1)
        pin(value)
        sleep_us(60)
        pin(1)
        sleep_us(1)
        self.enable_irq(i)

    def write_byte(self, value):
        for i in range(8):
            self.write_bit(value & 1)
            value >>= 1

    def write_bytes(self, buf):
        for b in buf:
            self.write_byte(b)

    def select_rom(self, rom):
        """
        Select a specific device to talk to. Pass in rom as a bytearray (8 bytes).
        """
        self.reset()
        self.write_byte(CMD_MATCHROM)
        self.write_bytes(rom)

    def crc8(self, data):
        """
        Compute CRC, based on tables
        """
        crc = 0
        for i in range(len(data)):
           crc ^= data[i] ## just re-using crc as intermediate
           crc = (self.crctab1[crc & 0x0f] ^
                  self.crctab2[(crc >> 4) & 0x0f])
        return crc

    def scan(self):
        """
        Return a list of ROMs for all attached devices.
        Each ROM is returned as a bytes object of 8 bytes.
        """
        devices = []
        diff = 65
        rom = False
        for i in range(0xff):
            rom, diff = self._search_rom(rom, diff)
            if rom:
                devices += [rom]
            if diff == 0:
                break
        return devices

    def _search_rom(self, l_rom, diff):
        if not self.reset():
            return None, 0
        self.write_byte(CMD_SEARCHROM)
        if not l_rom:
            l_rom = bytearray(8)
        rom = bytearray(8)
        next_diff = 0
        i = 64
        for byte in range(8):
            r_b = 0
            for bit in range(8):
                b = self.read_bit()
                if self.read_bit():
                    if b: # there are no devices or there is an error on the bus
                        return None, 0
                else:
                    if not b: # collision, two devices with different bit meaning
                        if diff > i or ((l_rom[byte] & (1 << bit)) and diff != i):
                            b = 1
                            next_diff = i
                self.write_bit(b)
                if b:
                    r_b |= 1 << bit
                i -= 1
            rom[byte] = r_b
        return rom, next_diff

class DS18X20(object):
    def __init__(self, onewire):
        self.ow = onewire
        self.roms = [rom for rom in self.ow.scan() if rom[0] == 0x10 or rom[0] == 0x28]
        self.fp = True
        try:
            1/1
        except TypeError:
            self.fp = False # floatingpoint not supported

    def isbusy(self):
        """
        Checks wether one of the DS18x20 devices on the bus is busy
        performing a temperature convertion
        """
        return not self.ow.read_bit()

    def start_conversion(self, rom=None):
        """
        Start the temp conversion on one DS18x20 device.
        Pass the 8-byte bytes object with the ROM of the specific device you want to read.
        If only one DS18x20 device is attached to the bus you may omit the rom parameter.
        """
        if (rom==None) and (len(self.roms)>0):
            rom=self.roms[0]
        if rom!=None:
            rom = rom or self.roms[0]
            ow = self.ow
            ow.reset()
            ow.select_rom(rom)
            ow.write_byte(0x44)  # Convert Temp

    def read_temp_async(self, rom=None):
        """
        Read the temperature of one DS18x20 device if the convertion is complete,
        otherwise return None.
        """
        if self.isbusy():
            return None
        if (rom==None) and (len(self.roms)>0):
            rom=self.roms[0]
        if rom==None:
            return None
        else:
            ow = self.ow
            ow.reset()
            ow.select_rom(rom)
            ow.write_byte(0xbe)  # Read scratch
            data = ow.read_bytes(9)
            crc = ow.crc8(data)
            if crc == 0:
                return self.convert_temp(rom[0], data)
            else:
                return None

    def convert_temp(self, rom0, data):
        """
        Convert the raw temperature data into degrees celsius and return as a fixed point with 2 decimal places.
        """
        temp_lsb = data[0]
        temp_msb = data[1]
        if rom0 == 0x10:
            if temp_msb != 0:
                # convert negative number
                temp_read = temp_lsb >> 1 | 0x80  # truncate bit 0 by shifting, fill high bit with 1.
                temp_read = -((~temp_read + 1) & 0xff) # now convert from two's complement
            else:
                temp_read = temp_lsb >> 1  # truncate bit 0 by shifting
            count_remain = data[6]
            count_per_c = data[7]
            if self.fp:
                return temp_read - 25 + (count_per_c - count_remain) / count_per_c
            else:
                return 100 * temp_read - 25 + (count_per_c - count_remain) // count_per_c
        elif rom0 == 0x28:
            temp = None
            if self.fp:
                temp = (temp_msb << 8 | temp_lsb) / 16
            else:
                temp = (temp_msb << 8 | temp_lsb) * 100 // 16
            if (temp_msb & 0xf8) == 0xf8: # for negative temperature
                temp -= 0x1000
            return temp
        else:
            assert False
