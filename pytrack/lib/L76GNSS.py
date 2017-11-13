import time
import gc
from machine import Timer

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

    def _convert_coords(self, lat, lat_dir, lon, lon_dir):
        lat_d = None
        lon_d = None
        try:
            lat_d = (float(lat) // 100) + ((float(lat) % 100) / 60)
            lon_d = (float(lon) // 100) + ((float(lon) % 100) / 60)
            if lat_dir == 'S':
                lat_d *= -1
            if lon_dir == 'W':
                lon_d *= -1
        except ValueError:
            pass
        return(lat_d, lon_d)

    def coordinates(self, debug=False):
        lat_d, lon_d, debug_timeout = None, None, False
        if self.timeout != None:
            self.chrono.reset()
            self.chrono.start()
        nmea = b''
        while True:
            if self.timeout != None and self.chrono.read() >= self.timeout:
                self.chrono.stop()
                chrono_timeout = self.chrono.read()
                self.chrono.reset()
                self.timeout_status = False
                debug_timeout = True
            if self.timeout_status != True:
                gc.collect()
                break
            nmea += self._read().lstrip(b'\n\n').rstrip(b'\n\n')
            gngll_idx = nmea.find(b'GNGLL')
            if gngll_idx >= 0:
                gngll = nmea[gngll_idx:]
                e_idx = gngll.find(b'\r\n')
                if e_idx >= 0:
                    try:
                        gngll = gngll[:e_idx].decode('ascii')
                        gngll_s = gngll.split(',')
                        lat_d, lon_d = self._convert_coords(
                            gngll_s[1], gngll_s[2], gngll_s[3], gngll_s[4])
                    except Exception:
                        pass
                    finally:
                        nmea = nmea[(gngll_idx + e_idx):]
                        gc.collect()
                        break
            else:
                gc.collect()
                if len(nmea) > 4096:
                    nmea = b''
            time.sleep(0.1)
        self.timeout_status = True
        if debug and debug_timeout:
            print('GPS timed out after %f seconds' % (chrono_timeout))
            return(None, None)
        else:
            return(lat_d, lon_d)

    def position(self, debug=False):
        lat_d, lon_d, alt, hdop, debug_timeout = None, None, None, None, False
        if self.timeout != None:
            self.chrono.reset()
            self.chrono.start()
        nmea = b''
        while True:
            if self.timeout != None and self.chrono.read() >= self.timeout:
                self.chrono.stop()
                chrono_timeout = self.chrono.read()
                self.chrono.reset()
                self.timeout_status = False
                debug_timeout = True
            if self.timeout_status != True:
                gc.collect()
                break
            nmea += self._read().lstrip(b'\n\n').rstrip(b'\n\n')
            gpgga_idx = nmea.find(b'GPGGA')
            if gpgga_idx >= 0:
                gpgga = nmea[gpgga_idx:]
                e_idx = gpgga.find(b'\r\n')
                if e_idx >= 0:
                    try:
                        gpgga = gpgga[:e_idx].decode('ascii')
                        gpgga_s = gpgga.split(',')
                        lat_d, lon_d = self._convert_coords(
                            gpgga_s[2], gpgga_s[3], gpgga_s[4], gpgga_s[5])
                        alt = gpgga_s[9]
                        hdop = gpgga_s[8]
                    except Exception:
                        pass
                    finally:
                        nmea = nmea[(gpgga_idx + e_idx):]
                        gc.collect()
                    if (lat_d is not None
                            and lon_d is not None
                            and alt is not None
                            and hdop is not None):
                        break
            else:
                gc.collect()
                if len(nmea) > 4096:
                    nmea = b''
            time.sleep(0.1)
        self.timeout_status = True
        if debug and debug_timeout:
            print('GPS timed out after %f seconds' % (chrono_timeout))
            return(None, None, None, None)
        else:
            return(lat_d, lon_d, alt, hdop)
