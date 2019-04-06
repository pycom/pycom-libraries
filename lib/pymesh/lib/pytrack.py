
# Copyright (c) 2019, Pycom Limited.
#
# This software is licensed under the GNU GPL version 3 or any
# later version, with permitted additional terms. For more information
# see the Pycom Licence v1.0 document supplied with this file, or
# available at https://www.pycom.io/opensource/licensing

from pycoproc import Pycoproc

__version__ = '1.4.0'

class Pytrack(Pycoproc):

    def __init__(self, i2c=None, sda='P22', scl='P21'):
        Pycoproc.__init__(self, i2c, sda, scl)
