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
import _thread

class Watchdog:

    def __init__(self):
        self.failed = False
        self.acknowledged = 0
        self._alarm = None
        self._lock = _thread.allocate_lock()

    def enable(self, timeout = 120):
        if self._alarm:
            self._alarm.cancel()
            self._alarm = None
            
        self._alarm = Timer.Alarm(self._check, s = timeout, periodic = True)

    def _check(self, alarm):
        with self._lock:
            if self.acknowledged > 0:
                self.failed = False
                self.acknowledged = 0
            else:
                self.failed = True

    def ack(self):
        with self._lock:
            self.acknowledged += 1

    def update_failed(self):
        with self._lock:
            return self.failed
