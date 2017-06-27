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

        self.timeout = timeout
        self.timeout_status = True
        self.i2c.writeto(GPS_I2CADDR, bytes([0]))

    def _read(self):
        return self.i2c.readfrom(GPS_I2CADDR, 64)

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

    def _gps_timeout(self, alarm):
        alarm.cancel()
        self.timeout_status = False

    def coordinates(self, debug=False):
        lat_d, lon_d = None, None
        if self.timeout != None:
            self._alarm = Timer.Alarm(self._gps_timeout, self.timeout, periodic=False)
        nmea = b''
        while True:
            if self.timeout_status != True:
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
                        lat_d, lon_d = self._convert_coords(gngll_s)
                    except Exception:
                        pass
                    finally:
                        nmea = nmea[(gngll_idx + e_idx):]
                        break
            else:
                if len(nmea) > 4096:
                    nmea = b''
            time.sleep(0.1)
            gc.collect()

        self.timeout_status = True
        if debug:
            print('GPS timed out after %d seconds' % (self.timeout))
        else:
            return(lat_d, lon_d)
