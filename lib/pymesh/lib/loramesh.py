
# Copyright (c) 2019, Pycom Limited.
#
# This software is licensed under the GNU GPL version 3 or any
# later version, with permitted additional terms. For more information
# see the Pycom Licence v1.0 document supplied with this file, or
# available at https://www.pycom.io/opensource/licensing

from network import LoRa
import socket
import time
import utime
import ubinascii
import pycom

from struct import *
from gps import Gps

__version__ = '6'
"""
__version__ = '6'
* added IPv6 unicast addresses as fdde:ad00:beef:0::<MAC>
"""

class Loramesh:
    """ Class for using Lora Mesh - openThread """

    STATE_DISABLED = const(0)
    STATE_DETACHED = const(1)
    STATE_CHILD = const(2)
    STATE_ROUTER = const(3)
    STATE_LEADER = const(4)
    STATE_LEADER_SINGLE = const(5)

    # rgb LED color for each state: disabled, detached, child, router, leader and single leader
    #RGBLED = [0x0A0000, 0x0A0000, 0x0A0A0A, 0x000A00, 0x00000A, 0x0A000A]
    RGBLED = [0x0A0000, 0x0A0000, 0x0A0A0A, 0x000A00, 0x0A000A, 0x000A0A]
    
    # TTN conf mode
    #RGBLED = [0x200505, 0x200505, 0x202020, 0x052005, 0x200020, 0x001818]
    
    # for outside/bright sun
    #RGBLED = [0xFF0000, 0xFF0000, 0x808080, 0x00FF00, 0x0000FF, 0xFF00FF]

    # mesh node state string
    STATE_STRING_LIST = ['Disabled','Detached', 'Child', 'Router', 'Leader']

    # address to be used for multicasting
    MULTICAST_MESH_ALL = 'ff03::1'
    MULTICAST_MESH_FTD = 'ff03::2'

    MULTICAST_LINK_ALL = 'ff02::1'
    MULTICAST_LINK_FTD = 'ff02::2'

    # Leader has an unicast IPv6: fdde:ad00:beef:0:0:ff:fe00:fc00
    LEADER_DEFAULT_RLOC = 'fc00'

    def __init__(self, lora):
        """ Constructor """
        self.lora = lora
        self.mesh = lora.Mesh() #start Mesh

        # get Lora MAC address
        #self.MAC = str(ubinascii.hexlify(lora.mac()))[2:-1]
        self.MAC = int(str(ubinascii.hexlify(lora.mac()))[2:-1], 16)

        #last 2 letters from MAC, as integer
        self.mac_short = self.MAC & 0xFFFF #int(self.MAC[-4:], 16)
        print("LoRa MAC: %s, short: %s"%(hex(self.MAC), self.mac_short))

        self.rloc16 = 0
        self.rloc = ''
        self.net_addr = ''
        self.ip_eid = ''
        self.ip_link = ''
        self.state = STATE_DISABLED

        # a dictionary with all direct neighbors
        # key is MAC for each neighbor
        # value is pair (age, mac, rloc16, role, rssi)
        #self.neigh_dict = {}
        self.router_data = RouterData()
        self.router_data.mac = self.MAC

        # a dictionary with all routers direct neighbors
        # key is MAC for each router
        # value is pair (age, rloc, neigh_num, (age, mac, rloc16, role, rssi))
        #self.leader_dict = {}
        self.leader_data = LeaderData()
        self.leader_data.mac = self.MAC

        # set of all MACS from whole current Mesh Network
        self.macs = set()
        self.macs_ts = -65535 # very old

        # list of all pairs (direct radio connections) inside Mesh
        self.connections = list()
        self.connections_ts = -65535 # very old

        # set a new unicast address
        self.unique_ip_prefix = "fdde:ad00:beef:0::"
        command = "ipaddr add " + self.ip_mac_unique(self.mac_short)
        self.mesh.cli(command)

    def ip_mac_unique(self, mac):
        ip = self.unique_ip_prefix + hex(mac & 0xFFFF)[2:]
        return ip

    def update_internals(self):
        self._state_update()
        self._rloc16_update()
        self._update_ips()
        self._rloc_ip_net_addr()

    def _rloc16_update(self):
        self.rloc16 = self.mesh.rloc()
        return self.rloc16

    def _update_ips(self):
        """ Updates all the unicast IPv6 of the Thread interface """
        ips = self.mesh.ipaddr()
        for line in ips:
            if line.startswith('fd'):
                # Mesh-Local unicast IPv6
                try:
                    addr = int(line.split(':')[-1], 16)
                except Exception:
                    continue
                if addr == self.rloc16:
                    # found RLOC
                    # RLOC IPv6 has x:x:x:x:0:ff:fe00:RLOC16
                    self.rloc = line
                elif ':0:ff:fe00:' not in line:
                    # found Mesh-Local EID
                    self.ip_eid = line
            elif line.startswith('fe80'):
                # Link-Local
                self.ip_link = line

    def is_connected(self):
        """ Returns true if it is connected if its Child, Router or Leader """
        connected = False
        if self.state in (STATE_CHILD, STATE_ROUTER, STATE_LEADER, STATE_LEADER_SINGLE):
            connected = True
        return connected

    def _state_update(self):
        """ Returns the Thread role """
        self.state = self.mesh.state()
        if self.state < 0:
            self.state = self.STATE_DISABLED
        return self.state

    def _rloc_ip_net_addr(self):
        """ returns the family part of RLOC IPv6, without last word (2B) """
        self.net_addr = ':'.join(self.rloc.split(':')[:-1]) + ':'
        return self.net_addr

    def state_string(self):
        if self.state >= len(self.STATE_STRING_LIST):
            return 'none'
        return self.STATE_STRING_LIST[self.state]

    def led_state(self):
        """ Sets the LED according to the Thread role """
        if self.state == STATE_LEADER and self.mesh.single():
            pycom.rgbled(self.RGBLED[self.STATE_LEADER_SINGLE])
        else:
            pycom.rgbled(self.RGBLED[self.state])

    def ip(self):
        """ Returns the IPv6 RLOC """
        return self.rloc

    # def parent_ip(self):
    #     # DEPRECATED, unused
    #     """ Returns the IP of the parent, if it's child node """
    #     ip = None
    #     state = self.state
    #     if state == STATE_CHILD or state == STATE_ROUTER:
    #         try:
    #             ip_words = self.rloc.split(':')
    #             parent_rloc = int(self.lora.cli('parent').split('\r\n')[1].split(' ')[1], 16)
    #             ip_words[-1] = hex(parent_rloc)[2:]
    #             ip = ':'.join(ip_words)
    #         except Exception:
    #             pass
    #     return ip


    # def neighbors_ip(self):
    #     # DEPRECATED, unused
    #     """ Returns a list with IP of the neighbors (children, parent, other routers) """
    #     state = self.state
    #     neigh = []
    #     if state == STATE_ROUTER or state == STATE_LEADER:
    #         ip_words = self.rloc.split(':')
    #         # obtain RLOC16 neighbors
    #         neighbors = self.lora.cli('neighbor list').split(' ')
    #         for rloc in neighbors:
    #             if len(rloc) == 0:
    #                 continue
    #             try:
    #                 ip_words[-1] = str(rloc[2:])
    #                 nei_ip = ':'.join(ip_words)
    #                 neigh.append(nei_ip)
    #             except Exception:
    #                     pass
    #     elif state == STATE_CHILD:
    #         neigh.append(self.parent_ip())
    #     return neigh

    # def cli(self, command):
    #     """ Simple wrapper for OpenThread CLI """
    #     return self.mesh.cli(command)

    def ipaddr(self):
        """ returns all unicast IPv6 addr """
        return self.mesh.ipaddr()

    def ping(self, ip):
        """ Returns ping return time, to an IP """
        res = self.cli('ping ' + str(ip))
        # '8 bytes from fdde:ad00:beef:0:0:ff:fe00:e000: icmp_seq=2 hlim=64 time=236ms\r\n'
        # 'Error 6: Parse\r\n'
        # no answer
        ret_time = -1
        try:
            ret_time = int(res.split('time=')[1].split('ms')[0])
        except Exception:
            pass
        return ret_time

    def blink(self, num = 3, period = .5, color = None):
        """ LED blink """
        if color is None:
            color = self.RGBLED[self.state]
        for _ in range(num):
            pycom.rgbled(0)
            time.sleep(period)
            pycom.rgbled(color)
            time.sleep(period)
        self.led_state()

    def neighbors_update(self):
        """ update neigh_dict from cli:'neighbor table' """
        """ >>> print(lora.cli("neighbor table"))
        | Role | RLOC16 | Age | Avg RSSI | Last RSSI |R|S|D|N| Extended MAC     |
        +------+--------+-----+----------+-----------+-+-+-+-+------------------+
        |   C  | 0x2801 | 219 |        0 |         0 |1|1|1|1| 0000000000000005 |
        |   R  | 0x7400 |   9 |        0 |         0 |1|0|1|1| 0000000000000002 |

        """
        x = self.mesh.neighbors()
        print("Neighbors Table: %s"%x)

        if x is None:
            # bad read, just keep previous neigbors
            return

        # clear all pre-existing neigbors
        self.router_data = RouterData()
        self.router_data.mac = self.MAC
        self.router_data.rloc16 = self.rloc16
        self.router_data.role = self.state
        self.router_data.ts = time.time()
        self.router_data.coord = Gps.get_location()

        for nei_rec in x:
            # nei_rec = (role=3, rloc16=10240, rssi=0, age=28, mac=5)
            age = nei_rec.age
            if age > 300:
                continue # shouln't add neighbors too old
            role = nei_rec.role
            rloc16 = nei_rec.rloc16
            # maybe we shouldn't add Leader (because this info is already available at Leader)
            # if rloc16 == self.leader_rloc():
            #   continue
            rssi = nei_rec.rssi
            mac = nei_rec.mac
            neighbor = NeighborData((mac, age, rloc16, role, rssi,))
            self.router_data.add_neighbor(neighbor)
            #print("new Neighbor: %s"%(neighbor.to_string()))
            #except:
            #    pass
        # add own info in dict
        #self.neigh_dict[self.MAC] = (0, self.rloc16, self.state, 0)
        print("Neighbors: %s"%(self.router_data.to_string()))
        return

    def leader_add_own_neigh(self):
        """ leader adds its own neighbors in leader_dict """
        self.leader_data.add_router(self.router_data)
        return

    def neighbors_pack(self):
        """ packs in a struct all neighbors as (MAC, RLOC16, Role, rssi, age) """
        data = self.router_data.pack()

        return data

    def routers_neigh_update(self, data_pack):
        """ unpacks the PACK_ROUTER_NEIGHBORS, adding them in leader_dict """
        # key is MAC for each router
        # value is pair (age, rloc, neigh_num, (age, mac, rloc16, role, rssi))
        router = RouterData(data_pack)
        self.leader_data.add_router(router)
        return

    def leader_dict_cleanup(self):
        """ cleanup the leader_dict for old entries """
        #print("Leader Data before cleanup: %s"%self.leader_data.to_string())
        self.leader_data.cleanup()
        print("Leader Data : %s"%self.leader_data.to_string())

    def routers_rloc_list(self, age_min, resolve_mac = None):
        """ return list of all routers IPv6 RLOC16
            if mac parameter is present, then returns just the RLOC16 of that mac, if found
        """
        mac_ip = None
        data = self.mesh.routers()
        print("Routers Table: ", data)
        '''>>> print(lora.cli('router table'))
        | ID | RLOC16 | Next Hop | Path Cost | LQ In | LQ Out | Age | Extended MAC     |
        +----+--------+----------+-----------+-------+--------+-----+------------------+
        | 12 | 0x3000 |       63 |         0 |     0 |      0 |   0 | 0000000000000002 |'''

        if data is None:
            # bad read
            return ()

        net_addr = self.net_addr
        routers_list = []
        for line in data:
            # line = (mac=123456, rloc16=20480, id=20, path_cost=0, age=7)
            age = line.age
            if age > 300:
                continue # shouldn't add/resolve very old Routers
            rloc16 = line.rloc16

            # check if it's own rloc16
            if rloc16 == self.rloc16:
                continue

            if resolve_mac is not None:
                if resolve_mac == line.mac:
                    mac_ip = rloc16
                    break
            
            # look for this router in Leader Data
            # if doesn't exist, add it to routers_list with max ts
            # if it exists, just add it with its ts
            last_ts = self.leader_data.get_mac_ts(line.mac)
            if time.time() - last_ts < age_min:
                continue # shouldn't add/resolve very "recent" Routers

            ipv6 = net_addr + hex(rloc16)[2:]
            routers_list.append((last_ts, ipv6))

        if resolve_mac is not None:
            print("Mac found in Router %s"%str(mac_ip))
            return mac_ip

        # sort the list in the ascending values of timestamp
        routers_list.sort()

        print("Routers list %s"%str(routers_list))
        return routers_list

    def leader_data_pack(self):
        """ creates packet with all Leader data, leader_dict """
        self.leader_data.rloc16 = self.rloc16
        data = self.leader_data.pack()
        return data

    def leader_data_unpack(self, data):
        self.leader_data = LeaderData(data)
        print("Leader Data : %s"%self.leader_data.to_string())
        return self.leader_data.ok

    def neighbor_resolve_mac(self, mac):
        mac_ip = self.router_data.resolve_mac(mac)
        return mac_ip

    def resolve_mac_from_leader_data(self, mac):
        mac_ip = self.leader_data.resolve_mac(mac)
        print("Mac %x found as IP %s"%(mac, str(mac_ip)))
        return mac_ip

    def macs_get(self):
        """ returns the set of the macs, hopefully it was received from Leader """
        #print("Macs: %s"%(str(self.macs)))
        return (self.macs, self.macs_ts)

    def macs_set(self, data):
        MACS_FMT = '!H'
        field_size = calcsize(MACS_FMT)
        #print("Macs pack: %s"%(str(data)))
        n, = unpack(MACS_FMT, data)
        #print("Macs pack(%d): %s"%(n, str(data)))
        index = field_size
        self.macs = set()

        for _ in range(n):
            mac, = unpack(MACS_FMT, data[index:])
            self.macs.add(mac)
            #print("Macs %d, %d: %s"%(index, mac, str(self.macs)))
            index = index + field_size

        self.macs_ts = time.time()
        pass

    def connections_get(self):
        """ returns the list of all connections inside Mesh, hopefully it was received from Leader """
        return (self.connections, self.connections_ts)

    def connections_set(self, data):
        CONNECTIONS_FMT = '!HHb'
        field_size = calcsize(CONNECTIONS_FMT)
        n, = unpack('!H', data)
        index = calcsize('!H')
        self.connections = list()
        for _ in range(n):
            #(mac1, mac2, rssi)
            record = unpack(CONNECTIONS_FMT, data[index:])
            self.connections.append(record)
            index = index + field_size
        self.connections_ts = time.time()
        pass

    def node_info_get(self, mac):
        """ returns the RouterData or NeighborData for the specified mac """
        #try to find it as router or a neighbor of a router
        node, role = self.leader_data.node_info_mac(mac)
        if node is None:
            return {}
        # try to create dict for RPC answer
        data = {}
        data['ip'] = node.rloc16
        data['r'] = node.role
        if role is self.STATE_CHILD:
            data['a'] = node.age
        elif role is self.STATE_ROUTER:
            data['a'] = time.time() - node.ts
            data['l'] = {'lng':node.coord[1], 'lat':node.coord[0]}
            data['nn'] = node.neigh_num()
            nei_macs = node.get_macs_set()
            data['nei'] = list()
            for nei_mac in nei_macs:
                nei = node.dict[nei_mac]
                data['nei'].append((nei.mac, nei.rloc16, nei.role, nei.rssi, nei.age))
        return data

    def node_info_set(self, data):
        (role, ) = unpack('!B', data)

        if role is self.STATE_ROUTER:
            router = RouterData(data[1:])
            self.leader_data.add_router(router)
            print("Added as router %s"%router.to_string())
        elif role is self.STATE_CHILD:
            node = NeighborData(data[1:])
            router = RouterData(node)
            self.leader_data.add_router(router)
            print("Added as Router-Neigh %s"%router.to_string())
        pass

class NeighborData:
    """ class for storing info about a Neighbor """
    #self.neigh_dict[mac] = (mac(2B), rloc16(2B), role(1B), rssi(signed char), age (1B))
    PACKING_FMT = '!HHBbB'

    def __init__(self, data = None):
        self.mac = 0
        self.age = 0xFFFF
        self.rloc16 = 0
        self.role = 0
        self.rssi = -150

        if data is None:
            return

        datatype = str(type(data))
        #print('NeighborData __init__ %s'%str(data))
        if datatype == "<class 'tuple'>":
            self._init_tuple(data)
        elif datatype == "<class 'bytes'>":
            self._init_bytes(data)
        #print('NeighborData done __init__')

    def _init_tuple(self, data):
        #print('_init_tuple %s'%str(data))
        (self.mac, self.age, self.rloc16, self.role, self.rssi) = data
        return

    def _init_bytes(self, data):
        #print('NeighborData._init_bytes %s'%str(data))
        self.mac, self.rloc16, self.role, self.rssi, self.age = unpack(self.PACKING_FMT,
            data[:self.pack_fmt_size()])
        return

    def pack(self):
        data = pack(self.PACKING_FMT, self.mac & 0xFFFF, self.rloc16, self.role, self.rssi, self.age)
        return data

    def to_string(self):
        x = 'MAC 0x%X, rloc16 0x%x, role %d, rssi %i, age %d'%(self.mac,
            self.rloc16, self.role, self.rssi, self.age)
        return x

    def pack_fmt_size(self):
        return calcsize(self.PACKING_FMT)

class RouterData:
    #self.neigh_dict[mac] = (age, rloc16, role, rssi)

    # MAC, rloc16, lat, lon, neighbors number
    PACK_HEADER_FMT = '!HHffB'

    def __init__(self, data = None):
        self.mac = 0
        self.rloc16 = 0
        self.role = 0
        self.ts = 0
        self.dict = {}
        self.pack_index_last = 0
        self.coord = (0.0, 0.0)

        if data is None:
            return

        datatype = str(type(data))
        if datatype == "<class 'bytes'>":
            self._init_bytes(data)
        elif datatype == "<class 'NeighborData'>":
            self._init_neighbordata(data)


    def _init_bytes(self, data_pack):

        #print('RouterData._init_bytes %s'%str(data_pack))
        index = calcsize(self.PACK_HEADER_FMT)
        (self.mac, self.rloc16, lat, lon, neigh_num) = \
            unpack(self.PACK_HEADER_FMT, data_pack[: index])
        
        self.coord = (lat, lon)

        self.role = Loramesh.STATE_ROUTER # forcer role as Router

        self.ts = time.time()

        for _ in range(neigh_num):
            neighbor  = NeighborData(data_pack[index:])

            index = index + neighbor.pack_fmt_size()

            #(mac, rloc16, role, rssi, age) = unpack('!QHBBB', data_pack[index : index_new])

            # don't add connection from Router to Leader (Leader already knows this)
            if neighbor.rloc16 == self.rloc16:
                continue
            #record = record + (age, mac, rloc16, role, rssi)
            self.dict[neighbor.mac] = neighbor

        self.pack_index_last = index
        return

    def _init_neighbordata(self, data):
        """ data is NeighborData """
        self.mac = data.mac
        self.rloc16 = data.rloc16
        self.role = data.role
        self.ts = time.time()
        return

    def add_neighbor(self, neighbor):
        self.dict[neighbor.mac] = neighbor
        #print("add_neighbor type: %s"%str(type(neighbor)))
        return

    def neigh_num(self):
        return len(self.dict)

    def pack(self):
        data = pack(self.PACK_HEADER_FMT, self.mac & 0xFFFF, \
            self.rloc16, self.coord[0], self.coord[1], len(self.dict))
        for mac, nei in self.dict.items():
            data = data + nei.pack()
        return data

    def clear(self):
        self.dict.clear()
        return

    def to_string(self):
        x = 'Router MAC 0x%X, rloc16 0x%x, coord %s, neigh_num %d, ts %d\n'\
            %(self.mac, self.rloc16, str(self.coord), len(self.dict), self.ts)
        for mac, nei in self.dict.items():
            #print("type: %s, %s"%(str(type(nei)),str(nei)))
            x = x + nei.to_string() + '\n'
        return x

    def resolve_mac(self, mac):
        """ returns the NeighborData for a specified mac """
        try:
            nei = self.dict[mac]
        except:
            nei = None
        return nei

    def as_dict(self):
        dict = {}
        dict['mac'] = self.mac
        dict['ip'] = self.rloc16
        dict['role'] = self.role
        dict['age'] = time.time() - self.ts
        dict['loc'] = self.coord[0]
        dict['ble'] = self.coord[1]
        return dict

    def get_all_pairs(self):
        lst = list()
        for mac, nei in self.dict.items():
            # consider all neighbors with mac smaller than parent's
            # so to not have pair (x, y) and (y, x)
            if mac < self.mac:
                pair = (mac, self.mac, nei.rssi)
                lst = lst + [pair]
            # else:
            #     break
        return lst

    def get_macs_set(self):
        """ returns set of all MACs neighbors """
        macs = set()
        for mac, _ in self.dict.items():
            macs.add(mac)
        return macs

class LeaderData:
    PACK_HEADER_FMT = '!QHB'

    def __init__(self, data = None):
        self.routers_num = 0
        self.mac = 0
        self.rloc16 = 0
        self.ts = 0
        self.dict = {}
        self.ok = False

        if data is None:
            return

        datatype = str(type(data))
        if datatype == "<class 'bytes'>":
            self._init_bytes(data)
        pass

    def _init_bytes(self, data_pack):

        #print('LeaderData._init_bytes %s'%str(data_pack))
        index = calcsize(self.PACK_HEADER_FMT)
        (self.mac, self.rloc16, routers_num) = unpack(self.PACK_HEADER_FMT, data_pack[: index])
        self.ts = time.time()

        for _ in range(routers_num):
            router = RouterData(data_pack[index:])

            index = index + router.pack_index_last

            self.dict[router.mac] = router
        self.ok = True
        pass

    def add_router(self, router_data):
        self.dict[router_data.mac] = router_data
        return

    def cleanup(self):
        for mac, router in self.dict.items():
            if time.time() - router.ts > 300:
                print("Deleted old Router %d"%mac)
                del self.dict[mac]
        return

    def pack(self):
        data = pack(self.PACK_HEADER_FMT, self.mac, self.rloc16, len(self.dict))
        for mac, value in self.dict.items():
            data = data + value.pack()
        return data

    def to_string(self):
        x = 'Leader data: MAC %X, rloc16 %x, routers_num %d\n'%(self.mac, self.rloc16, len(self.dict))
        for mac, router in self.dict.items():
            x = x + router.to_string()
        return x

    def node_info_mac(self, mac):
        # first check if the MAC is a known router
        router = self.dict.get(mac, None)
        if router is not None:
            return (router, Loramesh.STATE_ROUTER)

        # next check if MAC is a neighbor of a router
        child = None
        for _, router in self.dict.items():
            child = router.resolve_mac(mac)
            if child is not None:
                return (child, Loramesh.STATE_CHILD)
        return (None, None)

    def node_info_mac_pack(self, mac):
        node, role = self.node_info_mac(mac)
        if node is None:
            print("Node is None %d"%mac)
            return bytes()
        # pack type: RouterData or Child (basically NeighborData)
        data = pack('!B', role)
        data = data + node.pack()
        return data

    def resolve_mac(self, mac):
        """ returns the RLOC of the mac, if found """
        mac_ip = None
        data, _ = self.node_info_mac(mac)
        if data is not None:
            mac_ip = data.rloc16
        return mac_ip

    def records_num(self):
        return len(self.dict)

    def as_list(self):
        lst = list()
        for mac, router in self.dict.items():
            record = router.as_dict()
            lst = lst + [record]
        return lst

    def get_mesh_connections(self):
        lst = list()
        for mac, router in self.dict.items():
            record = router.get_all_pairs()
            lst = lst + record
        return lst

    def get_connections_pack(self):
        connections = self.get_mesh_connections()
        print("Connections ", connections)
        data = pack('!H', len(connections))
        for record in connections:
            (mac1, mac2, rssi) = record
            data = data + pack('!HHb', mac1, mac2, rssi)
        return data

    def get_macs_set(self):
        macs = set()
        for mac, router in self.dict.items():
            macs.add(mac)
            macs = macs.union(router.get_macs_set())
        return macs

    def get_macs_pack(self):
        macs = self.get_macs_set()
        data = pack('!H', len(macs))
        for mac in macs:
            data = data + pack('!H', mac)
        #print("Macs pack:%s"%(str(data)))
        return data

    def get_mac_ts(self, mac):
        # return the ts (last time Leader received pack) of a Router
        router = self.dict.get(mac, None)
        if router is None:
            # if this mac is not a router, just return ts as the oldest
            return 0
        return router.ts

