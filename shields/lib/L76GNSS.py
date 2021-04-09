#!/usr/bin/env python
#
# Copyright (c) 2019, Pycom Limited.
#
# This software is licensed under the GNU GPL version 3 or any
# later version, with permitted additional terms. For more information
# see the Pycom Licence v1.0 document supplied with this file, or
# available at https://www.pycom.io/opensource/licensing
#

from machine import Timer
import time
import gc
import binascii


class L76GNSS:

    GPS_I2CADDR = const(0x10)

    def __init__(self, pytrack=None, sda='P22', scl='P21', timeout=None, buffer=64):
        if pytrack is not None:
            self.i2c = pytrack.i2c
        else:
            from machine import I2C
            self.i2c = I2C(0, mode=I2C.MASTER, pins=(sda, scl))

        self.chrono = Timer.Chrono()

        self.timeout = timeout
        self.timeout_status = True
        self.buffer = buffer

        self.reg = bytearray(1)
        self.i2c.writeto(GPS_I2CADDR, self.reg)

    def _read(self):
        self.reg = self.i2c.readfrom(GPS_I2CADDR, self.buffer)
        return self.reg

    def _convert_coords(self, gngll_s):
        lat = gngll_s[1]
        lat_d = (float(lat) // 100) + ((float(lat) % 100) / 60)
        lon = gngll_s[3]
        lon_d = (float(lon) // 100) + ((float(lon) % 100) / 60)
        if gngll_s[2] == 'S':
            lat_d *= -1
        if gngll_s[4] == 'W':
            lon_d *= -1
        return(lat_d, lon_d)

    def coordinates(self, debug=False):
        lat_d, lon_d, debug_timeout = None, None, False
        if self.timeout is not None:
            self.chrono.reset()
            self.chrono.start()
        nmea = b''
        while True:
            if self.timeout is not None and self.chrono.read() >= self.timeout:
                self.chrono.stop()
                chrono_timeout = self.chrono.read()
                self.chrono.reset()
                self.timeout_status = False
                debug_timeout = True
            if not self.timeout_status:
                gc.collect()
                break
            nmea += self._read().lstrip(b'\n\n').rstrip(b'\n\n')
            gngll_idx = nmea.find(b'GNGLL')
            gpgll_idx = nmea.find(b'GPGLL')
            if gngll_idx < 0 and gpgll_idx >= 0:
                gngll_idx = gpgll_idx
            if gngll_idx >= 0:
                gngll = nmea[gngll_idx:]
                e_idx = gngll.find(b'\r\n')
                if e_idx >= 0:
                    try:
                        gngll = gngll[:e_idx].decode('ascii')
                        gngll_s = gngll.split(',')
                        lat_d, lon_d = self._convert_coords(gngll_s)
                    except Exception:
                        pass
                    finally:
                        nmea = nmea[(gngll_idx + e_idx):]
                        gc.collect()
                        break
            else:
                gc.collect()
                if len(nmea) > 410: # i suppose it can be safely changed to 82, which is longest NMEA frame
                    nmea = nmea[-5:] # $GNGL without last L
            time.sleep(0.1)
        self.timeout_status = True
        if debug and debug_timeout:
            print('GPS timed out after %f seconds' % (chrono_timeout))
            return(None, None)
        else:
            return(lat_d, lon_d)

    def dump_nmea(self):
        nmea = b''
        while True:
            nmea = self._read().lstrip(b'\n\n').rstrip(b'\n\n')
            start_idx = nmea.find(b'$')
            #print('raw[{}]: {}'.format(start_idx, nmea))
            if nmea is not None and len(nmea) > 0:
                if start_idx != 0:
                    if len(nmea[:start_idx]) > 1:
                        print('{}'.format(nmea[:start_idx].decode('ASCII')), end='')
                if len(nmea[start_idx:]) > 1:
                    print('{}'.format(nmea[start_idx:].decode('ASCII')), end='')

    def _checksum(self, nmeadata):
        calc_cksum = 0
        for s in nmeadata:
            calc_cksum ^= ord(s)
        return('{:02X}'.format(calc_cksum))

    def write(self, data):
        self.i2c.writeto(GPS_I2CADDR, '${}*{}\r\n'.format(data, self._checksum(data)) )
