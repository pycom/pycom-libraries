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

from pycoproc import Pycoproc

__version__ = '1.4.1'

class Pysense(Pycoproc):

    def __init__(self, i2c=None, sda='P22', scl='P21'):
        Pycoproc.__init__(self, Pycoproc.PYSENSE, i2c, sda, scl)
