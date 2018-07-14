from machine import Timer
import time
import gc
import binascii


class L76GNSS:

    GPS_I2CADDR = const(0x10)

    def __init__(self, pytrack=None, sda='P22', scl='P21', timeout=None):
        if pytrack is not None:
            self.i2c = pytrack.i2c
        else:
            from machine import I2C
            self.i2c = I2C(0, mode=I2C.MASTER, pins=(sda, scl))

        self.chrono = Timer.Chrono()

        self.timeout = timeout
        self.timeout_status = True

        self.reg = bytearray(1)
        self.i2c.writeto(GPS_I2CADDR, self.reg)

    def _read(self):
        self.reg = self.i2c.readfrom(GPS_I2CADDR, 64)
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

    def _convert_coords(self, gnrmc_s):
        lat = gnrmc_s[3]
        lat_d = (float(lat) // 100) + ((float(lat) % 100) / 60)
        lon = gnrmc_s[5]
        lon_d = (float(lon) // 100) + ((float(lon) % 100) / 60)
        if gnrmc_s[4] == 'S':
            lat_d *= -1
        if gnrmc_s[6] == 'W':
            lon_d *= -1
        return (lat_d, lon_d)

    def _convert_datetime(self, gnrmc_s):
        hours = int(float(gnrmc_s[1][:2]))
        minutes = int(float(gnrmc_s[1][2:4]))
        seconds = float(gnrmc_s[1][4:])

        day = int(float(gnrmc_s[9][:2]))
        month = int(float(gnrmc_s[9][2:4]))
        year = int(float(gnrmc_s[9][4:]))

        return (year, month, day, hours, minutes, seconds)

    def _convert_speed(self, gnrmc_s):
        return float(gnrmc_s[7]) * 0.514444444 # Convert knotts to m/s by multiplying by 0.514...

    def _convert_course(self, gnrmc_s):
        return float(gnrmc_s[8])

    def rmc(self, debug=False):
        lat_d, lon_d, debug_timeout = None, None, False
        if self.timeout is not None:
            self.chrono.reset()
            self.chrono.start()
        nmea = b''
        lat_d, lon_d = (None, None)
        datetime = None
        speed = None
        course = None
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
            gnrmc_idx = nmea.find(b'GNRMC')
            if gnrmc_idx >= 0:
                gnrmc = nmea[gnrmc_idx:]
                e_idx = gnrmc.find(b'\r\n')
                if e_idx >= 0:
                    try:
                        gnrmc = gnrmc[:e_idx].decode('ascii')
                        gnrmc_s = gnrmc.split(',')
                        lat_d, lon_d = self._convert_coords(gnrmc_s)
                        datetime = self._convert_datetime(gnrmc_s)
                        speed = self._convert_speed(gnrmc_s)
                        course = self._convert_course(gnrmc_s)
                    except Exception:
                        pass
                    finally:
                        nmea = nmea[(gnrmc_idx + e_idx):]
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
            return (None, None, None, None)
        else:
            return ((lat_d, lon_d), datetime, speed, course)

