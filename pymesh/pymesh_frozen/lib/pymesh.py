'''
Copyright (c) 2020, Pycom Limited.
This software is licensed under the GNU GPL version 3 or any
later version, with permitted additional terms. For more information
see the Pycom Licence v1.0 document supplied with this file, or
available at https://www.pycom.io/opensource/licensing
'''

import os
import machine
from machine import Timer
import _thread
import sys
import time

try:
    from mesh_interface import MeshInterface
except:
    from _mesh_interface import MeshInterface

try:
    from cli import Cli
except:
    from _cli import Cli

try:
    from pymesh_debug import *
except:
    from _pymesh_debug import *

try:
    from pymesh_config import PymeshConfig
except:
    from _pymesh_config import PymeshConfig


__version__ = '3'
"""
__version__ = '3'
* CLI can start/stop dynamically
* replaced all print with print_debug

__version__ = '2'
* added pause/resume

__version__ = '1'
* not-versioned prior 5th of Febr 2020

"""

class Pymesh:

    def __init__(self, config, message_cb):
        # print MAC, set MAC is given and restart

        self.config = config
        self.mesh = MeshInterface(self.config, message_cb)

        self.kill_all = False
        self.deepsleep_timeout = 0
        self.new_lora_mac = None

        # self.mesh.statistics.sleep_function = self.deepsleep_init
        self.mesh.sleep_function = self.deepsleep_init

        self.is_paused = False
        self._threads_start()

        self.cli = None

        self.ble_rpc = None
        if config.get("ble_api", False):
            try:
                from ble_rpc import BleRpc
            except:
                from _ble_rpc import BleRpc

            self.ble_rpc = BleRpc(self.config, self.mesh)

    def cli_start(self):
        if self.cli is None:
            self.cli = Cli(self.mesh, self)
            self.cli.sleep = self.deepsleep_init
            # self.cli_thread = _thread.start_new_thread(self.cli.process, (1, 2))
            self.cli.process(None, None)
    
    def deepsleep_now(self):
        """ prepare scripts for graceful exit, deepsleeps if case """
        print_debug(1, "deepsleep_now")
        self.mesh.pause()
        if self.ble_rpc:
            self.ble_rpc.terminate()
        # watchdog.timer_kill()
        # Gps.terminate()
        # self.mesh.statistics.save_all()
        print_debug(1, 'Cleanup code, all Alarms cb should be stopped')
        if self.new_lora_mac:
            fo = open("/flash/sys/lpwan.mac", "wb")
            mac_write=bytes([0, 0, 0, 0, 0, 0, (self.new_lora_mac >> 8) & 0xFF, self.new_lora_mac & 0xFF])
            fo.write(mac_write)
            fo.close()
            print_debug(1, "Really LoRa MAC set to " + str(self.new_lora_mac))
        if self.deepsleep_timeout > 0:
            print_debug(1, 'Going to deepsleep for %d seconds'%self.deepsleep_timeout)
            time.sleep(1)
            machine.deepsleep(self.deepsleep_timeout * 1000)
        else:
            raise Exception("Pymesh done")
            sys.exit()

    def deepsleep_init(self, timeout, new_MAC = None):
        """ initializes an deep-sleep sequence, that will be performed later """
        print_debug(3, "deepsleep_init")
        self.deepsleep_timeout = timeout
        self.kill_all = True
        if new_MAC:
            self.new_lora_mac = new_MAC
        return

    def process(self, arg1, arg2):
        try:
            while True:
                if self.kill_all:
                    self.deepsleep_now()
                if self.is_paused:
                     # break
                     _thread.exit()
                time.sleep(.5)
                pass

        except KeyboardInterrupt:
            print_debug(1, 'Got Ctrl-C')
        except Exception as e:
            sys.print_exception(e)

    def _threads_start(self):
        _thread.start_new_thread(self.process, (1,2))

    def pause(self):
        if self.is_paused:
            # print_debug(5, "Pymesh already paused")
            return

        print_debug(3, "Pymesh pausing")

        self.mesh.pause()
        if self.ble_rpc:
            self.ble_rpc.terminate()

        self.is_paused = True
        return

    def resume(self, tx_dBm = 14):
        if not self.is_paused:
            # print_debug(5, "Pymesh can't be resumed, not paused")
            return

        print_debug(3, "Pymesh resuming")
        self.is_paused = False
        self._threads_start()
        self.mesh.resume(tx_dBm)

        return

    def send_mess(self, mac, mess):
        """ send mess to specified MAC address
        data is dictionary data = {
            'to': 0x5,
            'b': 'text',
            'id': 12345,
            'ts': 123123123,
        } """
        data = {
            'to': mac,
            'b': mess,
            'id': 12345,
            'ts': time.time(),
        }
        return self.mesh.send_message(data)

    def br_set(self, prio, br_mess_cb):
        """ Enable BR functionality on this Node, with priority and callback """
        return self.mesh.br_set(True, prio, br_mess_cb)

    def br_remove(self):
        """ Disable BR functionality on this Node """
        return self.mesh.br_set(False)

    def status_str(self):
        message = "Role " + str(self.mesh.mesh.mesh.mesh.state()) + \
            ", Single " + str(self.mesh.mesh.mesh.mesh.single()) + \
            ", IPv6: " + str(self.mesh.mesh.mesh.mesh.ipaddr())
        return message

    def is_connected(self):
        return self.mesh.is_connected()

    def send_mess_external(self, ip, port, payload):
        """ send mess to specified IP+port address
        data is dictionary data = {
            'ip': '1:2:3::4',
            'port': 12345,
            'to': 0x5,
            'b': 'text',
            'id': 12345,
            'ts': 123123123,
        } """
        data = {
            'ip': ip,
            'port': port,
            'b': payload
        }
        return self.mesh.send_message(data)

    def config_get(self):
        return self.config

    def config_set(self, config_json_dict):
        PymeshConfig.write_config(config_json_dict)
        return self.config

    def mac(self):
        return self.mesh.mesh.MAC

    def ot_cli(self, command):
        """ Call OpenThread internal CLI """
        return self.mesh.ot_cli(command)

    def end_device(self, state = None):
        """ Set current node and End (Sleepy) Device, always a Child """
        return self.mesh.end_device(state)

    def leader_priority(self, weight = None):
        """ Set for the current node the Leader Weight;
        it's a 0 to 255 value, which increases/decreases probability to become Leader;
        by default any node has weight of 64 """
        return self.mesh.leader_priority(weight)

    def debug_level(self, level = None):
        """ Set the debug level, 0 - off; recommended levels are:
            DEBUG_DEBG = const(5)
            DEBUG_INFO = const(4)
            DEBUG_NOTE = const(3)
            DEBUG_WARN = const(2)
            DEBUG_CRIT = const(1)
            DEBUG_NONE = const(0) """
        return debug_level(level)
