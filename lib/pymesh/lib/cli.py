
# Copyright (c) 2019, Pycom Limited.
#
# This software is licensed under the GNU GPL version 3 or any
# later version, with permitted additional terms. For more information
# see the Pycom Licence v1.0 document supplied with this file, or
# available at https://www.pycom.io/opensource/licensing

import time
import json

__version__ = '1'
"""
* initial draft
"""

class Cli:
    """ class for CLI commands """

    def __init__(self, mesh, rpc_handler, ble_comm):
        self.mesh = mesh
        self.rpc_handler = rpc_handler
        self.ble_comm = ble_comm

        # lamda functions
        self.sleep = None
        return
    
    def process(self, arg1, arg2):
        last_mesh_pairs = []
        last_mesh_mac_list = []
        last_mesh_node_info = {}

        while True:
            time.sleep(.1)
            cmd = input('>')
            # print(cmd)

            # if cmd == 'rb':
            #     print('resetting unpacker buffer')
            #     self.rpc_handler = RPCHandler(rx_worker, tx_worker, mesh, ble_comm)

            if cmd == 'mac':
                print(self.mesh.mesh.mesh.MAC)

            elif cmd == 'mml':
                mesh_mac_list = self.rpc_handler.get_mesh_mac_list()
                if len(mesh_mac_list) > 0:
                    last_mesh_mac_list = mesh_mac_list
                print('mesh_mac_list ', json.dumps(last_mesh_mac_list))

            elif cmd == 'self':
                node_info = self.rpc_handler.get_node_info()
                print("self info:", node_info)

            elif cmd == 'mni':
                for mac in last_mesh_mac_list:
                    node_info = self.rpc_handler.get_node_info(mac)
                    time.sleep(.5)
                    if len(node_info) > 0:
                        last_mesh_node_info[mac] = node_info
                print('last_mesh_node_info', json.dumps(last_mesh_node_info))

            elif cmd == 'mp':
                mesh_pairs = self.rpc_handler.get_mesh_pairs()
                if len(mesh_pairs) > 0:
                    last_mesh_pairs = mesh_pairs
                print('last_mesh_pairs', json.dumps(last_mesh_pairs))

            elif cmd == 's':
                try:
                    to = int(input('(to)<'))
                    typ = input('(type, 0=text, 1=file, Enter for text)<')
                    if not typ:
                        typ = 0
                    else:
                        typ = int(typ)
                    txt = input('(text/filename)<')
                except:
                    print("Command parsing failed")
                    continue
                data = {
                    'to': to,
                    'ty': typ,
                    'b': txt,
                    'id': 12345,
                    'ts': int(time.time()),
                }
                print(self.rpc_handler.send_message(data))

            elif cmd == 'ws':
                to = int(input('(to)<'))
                print(self.rpc_handler.send_message_was_sent(to, 12345))

            elif cmd == 'rm':
                print(self.rpc_handler.receive_message())

            # elif cmd == 'gg':
            #     print("Gps:", (Gps.lat, Gps.lon))

            # elif cmd == 'gs':
            #     lat = float(input('(lat)<'))
            #     lon = float(input('(lon)<'))
            #     Gps.set_location(lat, lon)
            #     print("Gps:", (Gps.lat, Gps.lon))

            elif cmd == 'sleep':
                try:
                    timeout = int(input('(time[sec])<'))
                except:
                    continue
                if self.sleep:
                    self.sleep(timeout)

            elif cmd == "ble":
                # reset BLE connection
                self.ble_comm.restart()

            elif cmd == "stat":
                # do some statistics
                # data = []
                # data[0] = {'mac':6, 'n':3, 't':30, 's1':0, 's2':0}
                # data[0] = {'mac':6, 'n':3, 't':30, 's1':5, 's2':10}
                # data[2] = {'mac':6, 'n':30, 't':60, 's1':10, 's2':45}
                # for line in data:
                #     print()
                # print("1 = {'mac':6, 'n':30, 't':60, 's1':10, 's2':45}<'")
                # print("2 = {'mac':6, 'n':30, 't':60, 's1':10, 's2':45}<'")
                # print("3 = {'mac':6, 'n':30, 't':60, 's1':10, 's2':45}<'")
                # id = int(input('(choice 1-..)<'))
                data = {'mac':6, 'n':3, 't':60, 's1':3, 's2':8}
                res = self.mesh.statistics_start(data)
                print("ok? ", res)

            elif cmd == "stat?":
                try:
                    id = int(input('(id [Enter for all])<'))
                except:
                    id = 0
                res = self.mesh.statistics_get(id)
                print("ok? ", res)

            elif cmd == "rst":
                print("Mesh Reset NVM settings ... ")
                self.mesh.mesh.mesh.mesh.deinit()
                if self.sleep:
                    self.sleep(1)