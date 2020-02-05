from pycoproc import Pycoproc

__version__ = '1.0.1'

class Pyscan(Pycoproc):

    def __init__(self, i2c=None, sda='P22', scl='P21'):
        Pycoproc.__init__(self, Pycoproc.PYSCAN, i2c, sda, scl)
