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
    from pymesh_debug import print_debug
except:
    from _pymesh_debug import print_debug

class Pymesh:

    def __init__(self, config, message_cb):
        # print MAC, set MAC is given and restart
        
        self.config = config
        self.mesh = MeshInterface(config, message_cb)

        self.kill_all = False
        self.deepsleep_timeout = 0
        self.new_lora_mac = None
        # watchdog = Watchdog(meshaging, mesh)
        
        # self.mesh.statistics.sleep_function = self.deepsleep_init
        self.mesh.sleep_function = self.deepsleep_init

        self.cli = Cli(self.mesh)
        self.cli.sleep = self.deepsleep_init
        _thread.start_new_thread(self.process, (1,2))
        _thread.start_new_thread(self.cli.process, (1, 2))
        
        self.ble_rpc = None
        if config.get("ble_api", False):
            try:
                from ble_rpc import BleRpc
            except:
                from _ble_rpc import BleRpc

            self.ble_rpc = BleRpc(self.config, self.mesh)


    def deepsleep_now(self):
        """ prepare scripts for graceful exit, deepsleeps if case """
        print("deepsleep_now")
        self.mesh.timer_kill()
        if self.ble_rpc:
            self.ble_rpc.terminate()
        # watchdog.timer_kill()
        # Gps.terminate()
        # self.mesh.statistics.save_all()
        print('Cleanup code, all Alarms cb should be stopped')
        if self.new_lora_mac:
            fo = open("/flash/sys/lpwan.mac", "wb")
            mac_write=bytes([0, 0, 0, 0, 0, 0, (self.new_lora_mac >> 8) & 0xFF, self.new_lora_mac & 0xFF])
            fo.write(mac_write)
            fo.close()
            print("Really LoRa MAC set to", self.new_lora_mac)
        if self.deepsleep_timeout > 0:
            print('Going to deepsleep for %d seconds'%self.deepsleep_timeout)
            time.sleep(1)
            machine.deepsleep(self.deepsleep_timeout * 1000)
        else:
            raise Exception("Pymesh done")
            sys.exit()

    def deepsleep_init(self, timeout, new_MAC = None):
        """ initializes an deep-sleep sequence, that will be performed later """
        print("deepsleep_init")
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
                time.sleep(.5)
                pass

        except KeyboardInterrupt:
            print('Got Ctrl-C')
        except Exception as e:
            sys.print_exception(e)
        finally:
            print('finally')
            self.deepsleep_now()

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
        return self.mesh.debug_level(level)

