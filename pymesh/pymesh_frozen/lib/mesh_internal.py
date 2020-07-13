
# Copyright (c) 2020, Pycom Limited.
#
# This software is licensed under the GNU GPL version 3 or any
# later version, with permitted additional terms. For more information
# see the Pycom Licence v1.0 document supplied with this file, or
# available at https://www.pycom.io/opensource/licensing

import socket
import time
import utime
import ubinascii
import pycom
from machine import Timer
from struct import *

try:
    from loramesh import Loramesh
except:
    from _loramesh import Loramesh

try:
    from meshaging import *
except:
    from _meshaging import *

try:
    from pymesh_debug import print_debug
except:
    from _pymesh_debug import print_debug

__version__ = '7'
"""
__version__ = '7'
* added pause/resume

__version__ = '6'
* refactorized file send/receive in state machines

__version__ = '5'
* added file send/receive debug

__version__ = '4'
* add sending messages

__version__ = '3'
* initial version, in ble project
"""


class MeshInternal:
    """ Class for internal protocol inside Mesh network """

################################################################################
    # Border router constants

    BR_NET_ADDRESS = '2001:cafe:cafe:cafe::/64'

    EXTERNAL_NET = '1:2:3:4::'
    BR_HEADER_FMT = '!BHHHHHHHHH'
    BR_MAGIC_BYTE = const(0xBB)
    PACK_BR = const(0x90)

################################################################################

    # port number opened by all nodes for communicating neighbors
    PORT_MESH_INTERNAL = const(1234)

    # each packet starts with Type(1B) and Length(2B)
    PACK_HEADER_FMT = '!BH'
################################################################################
    # packs sent by Leader (received by Routers)

    # packet type for Leader to inquire Routers for their neighbors
    PACK_LEADER_ASK_NEIGH = const(0x80)

    # packet type for Leader to respond to with all its data
    # answer of PACK_ROUTER_ASK_LEADER_DATA
    PACK_LEADER_DATA = const(0x81)

    PACK_LEADER_MACS = const(0x82)
    PACK_LEADER_CONNECTIONS = const(0x83)
    PACK_LEADER_MAC_DETAILS = const(0x84)
################################################################################
    # packs sent by Routers (received by Leader)

    # packet type for Routers (containing their neighbors) sent to Leader
    # answer of PACK_LEADER_ASK_NEIGH
    PACK_ROUTER_NEIGHBORS = const(0xF0)

    # packet type for Router to interrogate Leader data
    PACK_ROUTER_ASK_LEADER_DATA = const(0xF1)

    PACK_ROUTER_ASK_MACS = const(0xF2)
    PACK_ROUTER_ASK_CONNECTIONS = const(0xF3)
    PACK_ROUTER_ASK_MAC_DETAILS = const(0xF4)

################################################################################

    # packet holding a message
    PACK_MESSAGE = const(0x10)

    # packet holding a message ACK
    PACK_MESSAGE_ACK = const(0x11)

################################################################################

    # constants for file sending
    #FILE_SEND_PACKSIZE = const(750)
    # PACK_FILE_SEND = const(0x20)
    # PACK_FILE_SEND_ACK = const(0x21)

################################################################################

    # timeout for Leader to interrogate Routers
    LEADER_INTERVAL = const(30)  # seconds

################################################################################

    def __init__(self, meshaging, config, message_cb):
        """ Constructor """
        # enable Thread interface
        self.mesh = Loramesh(config)

        self.MAC = self.mesh.MAC
        self.sock = None
        self.leader_ts = -self.LEADER_INTERVAL
        self.router_ts = 0
        self.leader_data_ok = False
        self.interrogate_leader_ts = -self.LEADER_INTERVAL
        self.messages = meshaging
        self.send_table = {}
        self.rx_cb_registered = False
        self.file_packsize = 0
        self.file_size  = 0
        self.send_f = None
        self.br_handler = None
        self.EXTERNAL_IP = self.EXTERNAL_NET + hex(self.MAC & 0xFFFF)[2:]
        self.ext_mesh_ts = -30
        self.message_cb = message_cb
        self.br_message_cb = None
        pass

    def pause(self):
        self.rx_cb_registered = False
        self.sock = None
        self.mesh.pause()

    def resume(self, tx_dBm = 14):
        self.mesh.resume(tx_dBm)

    def create_socket(self):
        """ create UDP socket """
        self.sock = socket.socket(socket.AF_LORA, socket.SOCK_RAW)
        self.sock.bind(self.PORT_MESH_INTERNAL)
        print_debug(5, "Socket created on port %d" % self.PORT_MESH_INTERNAL)

    def process_messages(self):
        """ consuming message queue """
        for mac, mess in self.messages.dict.items():
            if mess.state == Message.MESS_STATE_IP_PENDING:
                mess.ip = self.mesh.ip_mac_unique(mac)
                mess.mac = self.mesh.MAC
                mess.last_tx_ts = time.time()
                self.send_message(mess)
                mess.state = Message.MESS_STATE_SENT
            # elif mess.state == Message.MESS_STATE_SENT:
            #     # try to resend
            #     if time.time() - mess.last_tx_ts > 15:
            #         print_debug(3, "Re-transmit %x %s" % (mac, mess.ip))
            #         mess.last_tx_ts = time.time()
            #         self.send_message(mess)
        pass

    def send_message(self, message, answer = None):
        """ actual sending of a message on socket """
        payload = message.pack(self.MAC, answer)
        pack_type = self.PACK_MESSAGE
        # if message.type == message.TYPE_IMAGE:
        #     pack_type = self.PACK_FILE_SEND
        if payload:
            print_debug(4, "Send message " + str(payload))
            self.send_pack(pack_type, payload, message.ip)
        pass

    def is_connected(self):
        # if detached erase all leader_data
        # return true if either child, router or leader
        return self.mesh.is_connected()

    def led_state(self):
        self.mesh.led_state()

    def ip(self):
        return self.mesh.ip()

    # def _process_router(self):
    #     print_debug(3, "Process Router")
    #     # just update internal neighbor table
    #     self.mesh.neighbors_update()
    #     # add itself and neighbors in the leader data
    #     self.mesh.leader_add_own_neigh()

    def _process_leader(self):
        print_debug(3, "Process Leader")

        """
        if state == self.mesh.STATE_LEADER_SINGLE:
            # no neighbors routers, so nothing left to do
            return
        """
        # cleanup old entries
        self.mesh.leader_dict_cleanup()

        if time.time() - self.leader_ts < self.LEADER_INTERVAL:
            return

        # ask each router
        self.leader_ts = time.time()
        router_list = self.mesh.routers_rloc_list(60)
        router_num = min(len(router_list), 5)
        idx = 0
        for router_pair in router_list[:router_num]:
            (age, router) = router_pair
            self.send_pack(self.PACK_LEADER_ASK_NEIGH, '', router)
            print_debug(3, "Leader inquire Router %s" % router)
            idx = idx + 1
            if idx < router_num:
                time.sleep(.5)

    def br_send(self, data):
        """ if BR is available in whole Mesh, send some data """
        ret = False
        # first, make sure this node is not BR (BR data is sent directly)
        if len(self.mesh.mesh.border_router()) > 0:
            print_debug(3, "Node is BR, so shouldn't send data to another BR")
            return False

        # check if we have a BR network prefix in ipaddr
        for ip in self.mesh.ipaddr():
            if ip.startswith(self.BR_NET_ADDRESS[0:-4]):
                print_debug(3, "found BR address: %s"%ip)
                if time.time() - self.ext_mesh_ts >= 0:
                    ret = True
                    try:
                        ip = data['ip']
                        port = int(data['port'])
                        payload = data['b']
                    except:
                        print_debug(3, "Error parsing packet for Mesh-external")
                        ret = False
                    if ret:
                        self.send_pack(self.PACK_BR, payload, ip, port)
                        # self.send_pack(self.PACK_BR, self.debug_data(False), self.EXTERNAL_IP)
                        self.ext_mesh_ts = time.time()
                else:
                    print_debug(3, "BR sending too fast")
                    ret = False
        if not ret:
            print_debug(3, "no BR (mesh-external IPv6) found")
        return ret

    def process(self):
        self.mesh.update_internals()
        self.mesh.led_state()
        print_debug(3, "%d: MAC %s(%d), State %s, Single %s" % (time.time(),
            hex(self.MAC), self.MAC, self.mesh.state_string(), str(self.mesh.mesh.single())))
        print_debug(3, self.mesh.ipaddr())
        leader = self.mesh.mesh.leader()
        if leader is not None:
            print_debug(3,"Leader: mac %s, rloc %s, net: %s" %
                  (hex(leader.mac), hex(leader.rloc16), hex(leader.part_id)))
        if not self.mesh.is_connected():
            return  # nothing to do

        # create socket
        if self.sock is None:
            self.create_socket()

        if not self.rx_cb_registered:
            self.rx_cb_registered = True
            self.mesh.mesh.rx_cb(self.receive_all_data, None)

        # update internal neighbor table
        self.mesh.neighbors_update()

        self.mesh.leader_add_own_neigh()

        # # if file to be sent
        # if self.send_f is not None:
        #     data, ip = self.send_f.process(None)
        #     if len(data) > 0:
        #         self.send_pack(self.PACK_FILE_SEND, data, ip)

        # if self.mesh.state == self.mesh.STATE_LEADER:
        #     self._process_leader()
        return

    def debug_data(self, br = True):
        """ Creating a debug string """
        if br:
            # BR can send more data
            data = "%d: MAC %s(%d), State %s, Single %s" % (time.time(),
                hex(self.MAC), self.MAC, self.mesh.state_string(), str(self.mesh.mesh.single()))
            data = data + "\n" + str(self.mesh.ipaddr())
            data = data + "\n" + str(self.mesh.mesh.routers())
            data = data + "\n" + str(self.mesh.mesh.neighbors())
        else:
            # normal node sends data over Mesh to BR, so less/compressed data
            data = "%d: M=%d, %s," % (time.time(), self.MAC, self.mesh.state_string())
            data = data +" nei:" + str(self.mesh.mesh.neighbors())
        return data

    def border_router(self, enable, prio = 0, br_mess_cb = None):
        """ Disables/Enables the Border Router functionality, with priority and callback """
        net_list = self.mesh.mesh.border_router()
        print_debug(3, "State:" + str(enable) + "BR: "+ str(net_list))

        if not enable:
            # disable all BR network registrations (possible multiple)
            self.br_handler = None
            for net in net_list:
                self.mesh.mesh.border_router_del(net.net)
            print_debug(3, "Done remove BR")
        else:
            self.br_handler = br_mess_cb
            # check if BR already added
            try:
                # print_debug(3, net[0].net)
                # print_debug(3, self.BR_NET_ADDRESS)
                # if net[0].net != self.BR_NET_ADDRESS:
                if not net_list[0].net.startswith(self.BR_NET_ADDRESS[0:-3]):
                    # enable BR
                    self.mesh.mesh.border_router(self.BR_NET_ADDRESS, prio)
                    print_debug(3, "Done add BR")
            except:
                # enable BR
                self.mesh.mesh.border_router(self.BR_NET_ADDRESS, prio)
                print_debug(3, "Force add BR")

        # print again the BR, to confirm
        net_list = self.mesh.mesh.border_router()
        print_debug(3, "BR: " + str(net_list))
        pass

    def _check_to_send(self, pack_type, ip):
        send_it = True
        try:
            # invent some small hash, to uniquely identify packet
            key = (100 * pack_type) + int(ip[-4:], 16)
        except:
            # just send it
            #print_debug(3, "just send it, ? ", ip)
            send_it = False
        if not send_it:
            return True

        now = time.time()
        try:
            timestamp = self.send_table[key]
            if now - timestamp < 35:
                send_it = False
            else:
                self.send_table[key] = now
        except:
            #print_debug(3, "%s not in send_table"%str(key))
            send_it = True

        if send_it:
            # mark packet as sent now
            self.send_table[key] = now
            #print_debug(3, "Packet sent now")
        return send_it  # packet already send

    def send_pack(self, pack_type, data, ip, port=PORT_MESH_INTERNAL):
        if self.sock is None:
            return False

        print_debug(3, "Send pack: 0x%X to IP %s" % (pack_type, ip))

        # check not to send same (packet, destination) too often
        # if not self._check_to_send(pack_type, ip):
        #     print_debug(3, "NO send")
        #     return False

        sent_ok = True
        header = pack('!BH', pack_type, len(data))

        try:
            self.sock.sendto(header + data, (ip, port))
            #self.mesh.blink(2, .1)
        except Exception as ex:
            print_debug(3, "Socket.sendto exception: {}".format(ex))
            sent_ok = False
        return sent_ok

    def get_type(self, data):

        (pack_type, len1) = unpack(self.PACK_HEADER_FMT,
                                   data[:calcsize(self.PACK_HEADER_FMT)])
        data = data[calcsize(self.PACK_HEADER_FMT):]

        len2 = len(data)
        if len1 != len2:
            print_debug(3, "PACK_HEADER length not ok %d %d" % (len1, len2))
            print_debug(3, str(data))
            return

        return (pack_type, data)

    def get_mesh_pairs(self):
        """ Returns the list of all pairs of nodes directly connected inside mesh """
        # try to obtain if we already have them
        (pairs, pairs_ts) = self.mesh.connections_get()

        if len(pairs) or time.time() - pairs_ts > 30:
            # if there's none or too old, require new one from Leader
            leader_ip = self.mesh._rloc_ip_net_addr() + self.mesh.LEADER_DEFAULT_RLOC
            self.send_pack(self.PACK_ROUTER_ASK_CONNECTIONS, '', leader_ip)

        return pairs

    def get_all_macs_set(self):
        """ Returns the set of all distinct MACs of all nodes inside mesh """
        # try to obtain if we already have them
        (macs, macs_ts) = self.mesh.macs_get()

        if len(macs) == 0 or time.time() - macs_ts > 30:
            # if there's none or too old, require new one from Leader
            leader_ip = self.mesh._rloc_ip_net_addr() + self.mesh.LEADER_DEFAULT_RLOC
            self.send_pack(self.PACK_ROUTER_ASK_MACS, '', leader_ip)

        return macs

    def node_info(self, mac):
        """ Returns the info about a specified Node inside mesh """
        # try to obtain if we already have them
        node_data = self.mesh.node_info_get(mac)

        if len(node_data) == 0 or node_data['a'] > 120 or \
            node_data.get('nn', None) is None:
            # if there's none or too old, require new one from the node
            node_ip = self.mesh.ip_mac_unique(mac)
            payload = pack('!H', mac)
            self.send_pack(self.PACK_ROUTER_ASK_MAC_DETAILS,
                           payload, node_ip)

        return node_data

    def receive_all_data(self, arg):
        """ receives all packages on socket """

        while True:
            rcv_data, rcv_addr = self.sock.recvfrom(1024)
            if len(rcv_data) == 0:
                break  # out of while, no packet
            rcv_ip = rcv_addr[0]
            rcv_port = rcv_addr[1]
            print_debug(4, 'Incoming %d bytes from %s (port %d):' %
                  (len(rcv_data), rcv_ip, rcv_port))
            # print_debug(3, rcv_data)
            print_debug(5, str(self.mesh.lora.stats()))

            # check if Node is BR
            if self.br_handler:
                #check if data is for the external of the Pymesh (for Pybytes)
                if rcv_data[0] == self.BR_MAGIC_BYTE and len(rcv_data) >= calcsize(self.BR_HEADER_FMT):
                    br_header = unpack(self.BR_HEADER_FMT, rcv_data)
                    print_debug(3, "BR pack, IP dest: %x:%x:%x:%x:%x:%x:%x:%x (port %d)"%(
                        br_header[1],br_header[2],br_header[3],br_header[4],
                        br_header[5],br_header[6],br_header[7],br_header[8], br_header[9]))
                    rcv_data = rcv_data[calcsize(self.BR_HEADER_FMT):]

                    dest_ip = "%x:%x:%x:%x:%x:%x:%x:%x"%(
                        br_header[1],br_header[2],br_header[3],br_header[4],
                        br_header[5],br_header[6],br_header[7],br_header[8])

                    dest_port = br_header[9]

                    print_debug(3, rcv_data)
                    (type, rcv_data) = self.get_type(rcv_data)
                    print_debug(3, rcv_data)

                    self.br_handler(rcv_ip, rcv_port, rcv_data, dest_ip, dest_port)
                    return # done, no more parsing as this pack was for BR

            # check packet type
            (type, rcv_data) = self.get_type(rcv_data)
            # LEADER
            if type == self.PACK_ROUTER_NEIGHBORS:
                print_debug(3, "PACK_ROUTER_NEIGHBORS received")
                self.mesh.routers_neigh_update(rcv_data)
                # no answer
            # elif type == self.PACK_ROUTER_ASK_LEADER_DATA:
            #     print_debug(3, "PACK_ROUTER_ASK_LEADER_DATA received")
            #     # send answer with Leader data
            #     pack = self.mesh.leader_data_pack()
            #     self.send_pack(self.PACK_LEADER_DATA, pack, rcv_ip)

            # ROUTER
            elif type == self.PACK_LEADER_ASK_NEIGH:
                print_debug(3, "PACK_LEADER_ASK_NEIGH received")
                payload = self.mesh.neighbors_pack()
                #time.sleep(.2)
                self.send_pack(self.PACK_ROUTER_NEIGHBORS, payload, rcv_ip)
            # elif type == self.PACK_LEADER_DATA:
            #     print_debug(3, "PACK_LEADER_DATA received")
            #     if self.mesh.leader_data_unpack(rcv_data):
            #         self.interrogate_leader_ts = time.time()

            # ALL NODES
            elif type == self.PACK_MESSAGE:
                print_debug(3, "PACK_MESSAGE received")
                # add new pack received
                message = Message(rcv_data)
                # print_debug(3, message.payload)
                message.ip = rcv_ip
                self.messages.add_rcv_message(message)

                # send back ACK
                self.send_pack(self.PACK_MESSAGE_ACK, message.pack_ack(self.MAC), rcv_ip)

                # forward message to user-application layer
                if self.message_cb:
                    self.message_cb(rcv_ip, rcv_port, message.payload)


            elif type == self.PACK_MESSAGE_ACK:
                print_debug(3, "PACK_MESSAGE_ACK received")
                # mark message as received
                self.messages.rcv_ack(rcv_data)

            elif type == self.PACK_ROUTER_ASK_MACS:
                print_debug(3, "PACK_ROUTER_ASK_MACS received")
                payload = self.mesh.leader_data.get_macs_pack()
                self.send_pack(self.PACK_LEADER_MACS, payload, rcv_ip)

            elif type == self.PACK_LEADER_MACS:
                print_debug(3, "PACK_LEADER_MACS received")
                self.mesh.macs_set(rcv_data)

            elif type == self.PACK_ROUTER_ASK_CONNECTIONS:
                print_debug(3, "PACK_ROUTER_ASK_CONNECTIONS received")
                payload = self.mesh.leader_data.get_connections_pack()
                self.send_pack(self.PACK_LEADER_CONNECTIONS, payload, rcv_ip)

            elif type == self.PACK_LEADER_CONNECTIONS:
                print_debug(3, "PACK_LEADER_CONNECTIONS received")
                self.mesh.connections_set(rcv_data)

            elif type == self.PACK_ROUTER_ASK_MAC_DETAILS:
                print_debug(3, "PACK_ROUTER_ASK_MAC_DETAILS received")
                (mac_req, ) = unpack('!H', rcv_data)
                print_debug(3, str(mac_req))
                payload = self.mesh.leader_data.node_info_mac_pack(mac_req)
                if len(payload) > 0:
                    self.send_pack(self.PACK_LEADER_MAC_DETAILS,
                                   payload, rcv_ip)
                else:
                    print_debug(3, "No info found about MAC %d"%mac_req)

            elif type == self.PACK_LEADER_MAC_DETAILS:
                print_debug(3, "PACK_LEADER_MAC_DETAILS received")
                self.mesh.node_info_set(rcv_data)

            # elif type == self.PACK_FILE_SEND:
            #     print_debug(3, "PACK_FILE_SEND received")
            #     payload = pack("!Q", self.MAC)
            #     self.send_pack(self.PACK_FILE_SEND_ACK, payload, rcv_ip)
            #     # rcv data contains '!QHH' as header
            #     chunk = len(rcv_data) -12
            #     self.file_size += chunk
            #     print_debug(3, "size: %d, chunk %d" % (self.file_size, chunk))
            #     file_handler = "ab" # append, by default
            #     if chunk > self.file_packsize:
            #         # started receiving a new file
            #         print_debug(3, "started receiving a new image")
            #         file_handler = "wb" # write/create new file
            #         self.file_packsize = chunk
            #     elif chunk < self.file_packsize:
            #         print_debug(3, "DONE receiving the image")
            #         # done receiving the file
            #         self.file_packsize = 0
            #         self.file_size = 0
            #         self.messages.file_transfer_done(rcv_data[:12])
            #     # else:
            #     #     #middle of the file, just write data
            #     #     self.file.write(rcv_data)
            #     with open('/flash/dog_rcv.jpg', file_handler) as file:
            #         file.write(rcv_data[12:])
            #         print_debug(3, "writing the image")


            # elif type == self.PACK_FILE_SEND_ACK:
            #     mac_rcv = unpack("!Q", rcv_data)
            #     print_debug(3, "PACK_FILE_SEND_ACK received from MAC %d"%mac_rcv)
            #     mac_rcv = 6
            #     message = self.messages.dict.get(mac_rcv, None)
            #     if message:
            #         print_debug(3, "message found")
            #         self.send_message(message, rcv_data)
            #     else:
            #         print_debug(3, "message NOT found ", mac_rcv, self.messages.dict)

            else:
                print_debug(3, "Unknown packet, type: 0x%X" % (type))
                print_debug(3, str(rcv_data))

        pass
