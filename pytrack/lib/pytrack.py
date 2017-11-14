from pic_mcu import Pic_mcu

__version__ = '1.4.0'

class Pytrack(Pic_mcu):

    def __init__(self, i2c=None, sda='P22', scl='P21'):
        Pic_mcu.__init__(self, i2c, sda, scl)
