
# Copyright (c) 2020, Pycom Limited.
#
# This software is licensed under the GNU GPL version 3 or any
# later version, with permitted additional terms. For more information
# see the Pycom Licence v1.0 document supplied with this file, or
# available at https://www.pycom.io/opensource/licensing

import pycom

# recommended debug levels, from the most verbose to off
DEBUG_DEBG = const(5)
DEBUG_INFO = const(4)
DEBUG_NOTE = const(3)
DEBUG_WARN = const(2)
DEBUG_CRIT = const(1)
DEBUG_NONE = const(0)

try:
    DEBUG = pycom.nvs_get('pymesh_debug')
except:
    DEBUG = None


def print_debug(level, msg):
    """Print log messages into console."""
    if DEBUG is not None and level <= DEBUG:
        print(msg)

def debug_level(level):
    global DEBUG
    DEBUG = level
    pycom.nvs_set('pymesh_debug', DEBUG)
    