
# Copyright (c) 2019, Pycom Limited.
#
# This software is licensed under the GNU GPL version 3 or any
# later version, with permitted additional terms. For more information
# see the Pycom Licence v1.0 document supplied with this file, or
# available at https://www.pycom.io/opensource/licensing

import time
import json
import sys

try:
    from pymesh_debug import print_debug
except:
    from _pymesh_debug import print_debug

try:
    from gps import Gps
except:
    from _gps import Gps

__version__ = '1'
"""
* initial draft
"""

class Cli:
    """ class for CLI commands """

    def __init__(self, mesh):
        self.mesh = mesh
        # self.rpc_handler = rpc_handler
        # self.ble_comm = ble_comm

        # lamda functions
        self.sleep = None
        return
    
    def process(self, arg1, arg2):
        last_mesh_pairs = []
        last_mesh_mac_list = []
        last_mesh_node_info = {}

        try:
            while True:
                time.sleep(.1)
                cmd = input('>')
                # cmd = " "
                # time.sleep(3)
                # print("cli")

                # if cmd == 'rb':
                #     print('resetting unpacker buffer')
                #     self.rpc_handler = RPCHandler(rx_worker, tx_worker, mesh, ble_comm)

                if cmd == 'ip':
                    print(self.mesh.ip())

                elif cmd == 'mac':
                    # read/write LoRa MAC address
                    try:
                        id = int(input('(new LoRa MAC (0-64k) [Enter for read])<'))
                    except:
                        print(self.mesh.mesh.mesh.MAC)
                        continue
                    id = id & 0xFFFF # just 2B value
                    # it's actually set in main.py (main thread)
                    print("LoRa MAC set to", id)
                    self.sleep(1, id) # force restart

                elif cmd == 'mml':
                    mesh_mac_list = self.mesh.get_mesh_mac_list()
                    if len(mesh_mac_list) > 0:
                        last_mesh_mac_list = mesh_mac_list
                    print('mesh_mac_list ', json.dumps(last_mesh_mac_list))

                elif cmd == 'self':
                    node_info = self.mesh.get_node_info()
                    print("self info:", node_info)

                elif cmd == 'mni':
                    for mac in last_mesh_mac_list:
                        node_info = self.mesh.get_node_info(mac)
                        time.sleep(.5)
                        if len(node_info) > 0:
                            last_mesh_node_info[mac] = node_info
                    print('last_mesh_node_info', json.dumps(last_mesh_node_info))

                elif cmd == 'mp':
                    mesh_pairs = self.mesh.get_mesh_pairs()
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
                    print(self.mesh.send_message(data))

                elif cmd == 'ws':
                    to = int(input('(to)<'))
                    try:
                        id = int(input('(id, default 12345)<'))
                    except:
                        id = 12345
                    print(self.mesh.mesage_was_ack(to, id))

                elif cmd == 'rm':
                    print(self.mesh.get_rcv_message())

                elif cmd == 'gps':
                    try:
                        lat = float(input('(lat [Enter for read])<'))
                        lon = float(input('(lon)<'))
                    except:
                        print("Gps:", (Gps.lat, Gps.lon))
                        continue
                    
                    Gps.set_location(lat, lon)
                    print("Gps:", (Gps.lat, Gps.lon))

                elif cmd == 'sleep':
                    try:
                        timeout = int(input('(time[sec])<'))
                    except:
                        continue
                    if self.sleep:
                        self.sleep(timeout)

                # elif cmd == "ble":
                #     # reset BLE connection
                #     self.ble_comm.restart()

                # elif cmd == "stat":
                #     # do some statistics
                #     # data = []
                #     # data[0] = {'mac':6, 'n':3, 't':30, 's1':0, 's2':0}
                #     # data[0] = {'mac':6, 'n':3, 't':30, 's1':5, 's2':10}
                #     # data[2] = {'mac':6, 'n':30, 't':60, 's1':10, 's2':45}
                #     # for line in data:
                #     #     print()
                #     # print("1 = {'mac':6, 'n':30, 't':60, 's1':10, 's2':45}<'")
                #     # print("2 = {'mac':6, 'n':30, 't':60, 's1':10, 's2':45}<'")
                #     # print("3 = {'mac':6, 'n':30, 't':60, 's1':10, 's2':45}<'")
                #     # id = int(input('(choice 1-..)<'))
                #     data = {'mac':6, 'n':3, 't':60, 's1':3, 's2':8}
                #     res = self.mesh.statistics_start(data)
                #     print("ok? ", res)

                # elif cmd == "stat?":
                #     try:
                #         id = int(input('(id [Enter for all])<'))
                #     except:
                #         id = 0
                #     res = self.mesh.statistics_get(id)
                #     print("ok? ", res)

                elif cmd == "rst":
                    print("Mesh Reset NVM settings ... ")
                    self.mesh.mesh.mesh.mesh.deinit()
                    if self.sleep:
                        self.sleep(1)
                        
                # elif cmd == "pyb":
                #     # print("Pybytes debug menu, Pybytes connection is ", Pybytes_wrap.is_connected())
                #     state = 1
                #     timeout = 120
                #     try:
                #         state = int(input('(Debug 0=stop, 1=start [Default start])<'))
                #     except:
                #         pass
                #     try:
                #         timeout = int(input('(Pybytes timeout [Default 120 sec])<'))
                #     except:
                #         pass
                #     self.mesh.pybytes_config((state == 1), timeout)

                elif cmd == "br":
                    state = 2 # default display BR
                    try:
                        state = int(input('(state 0=Disable, 1=Enable, 2=Display [Default Display])<'))
                    except:
                        pass

                    if state == 2:
                        print("Border Router state: ", self.mesh.mesh.mesh.mesh.border_router())
                    elif state == 1:
                        # Enable BR
                        prio = 0 # default normal priority
                        try:
                            prio = int(input('(priority -1=Low, 0=Normal or 1=High [Default Normal])<'))
                        except:
                            pass
                        self.mesh.br_set(True, prio, self.new_br_message_cb)
                    else:
                        # disable BR function
                        self.mesh.br_set(False)

                elif cmd == "brs":
                    """ send data to BR """
                    ip_default = "1:2:3::4"
                    port = 5555
                    try:
                        payload = input("(message<)")
                        ip = input("(IP destination, Mesh-external [Default: 1:2:3::4])<")
                        if len(ip) == 0:
                            ip = ip_default
                        port = int(input("(port destination [Default: 5555])<"))
                    except:
                        pass
                    data = {
                        'ip': ip,
                        'port': port,
                        'b': payload 
                    }
                    print("Send BR message:", data)
                    self.mesh.send_message(data)

                elif cmd == "buf":
                    print("Buffer info:",self.mesh.mesh.mesh.mesh.cli("bufferinfo"))
                    
                elif cmd == "ot":
                    cli = input('(openthread cli)<')
                    print(self.mesh.mesh.mesh.mesh.cli(cli))

                elif cmd == "debug":
                    ret = input('(debug level[0-5])<')
                    try:
                        level = int(ret)
                        self.mesh.debug_level(level)
                    except:
                        print_debug(1, "error parsing")
                
                elif cmd == "config":
                    print(self.mesh.config)

                else:
                    print("List of available commands")
                    print("ip - display current IPv6 unicast addresses")
                    print("mac - set or display the current LoRa MAC address")
                    print("self - display all info about current node")
                    print("mml - display the Mesh Mac List (MAC of all nodes inside this Mesh), also inquires Leader")
                    print("mp - display the Mesh Pairs (Pairs of all nodes connections), also inquires Leader")
                    print("s - send message")
                    print("ws - verifies if message sent was acknowledged")
                    print("rm - verifies if any message was received")
                    print("sleep - deep-sleep")
                    # print("stat - start statistics")
                    # print("stat? - display statistics")
                    print("br - enable/disable or display the current Border Router functionality")
                    print("brs - send packet for Mesh-external, to BR, if any")
                    print("rst - reset NOW, including NVM Pymesh IPv6")
                    print("buf - display buffer info")
                    print("ot - sends command to openthread internal CLI")
                    print("debug - set debug level")
                    print("config - print config file contents")
                    print("gps - get/set location coordinates")
                    
        except KeyboardInterrupt:
            print('cli Got Ctrl-C')
        except Exception as e:
            sys.print_exception(e)
        finally:
            print('cli finally')
            self.sleep(0)

    def new_br_message_cb(self, rcv_ip, rcv_port, rcv_data, dest_ip, dest_port):
        ''' callback triggered when a new packet arrived for the current Border Router,
        having destination an IP which is external from Mesh '''
        print('CLI BR default handler')
        print('Incoming %d bytes from %s (port %d), to external IPv6 %s (port %d)' %
                (len(rcv_data), rcv_ip, rcv_port, dest_ip, dest_port))
        print(rcv_data)

        # user code to be inserted, to send packet to the designated Mesh-external interface
        # ...
        return