
# Copyright (c) 2019, Pycom Limited.
#
# This software is licensed under the GNU GPL version 3 or any
# later version, with permitted additional terms. For more information
# see the Pycom Licence v1.0 document supplied with this file, or
# available at https://www.pycom.io/opensource/licensing

import time
from struct import *

__version__ = '1'
"""
* initial version
"""


class Meshaging:
    """ class that manages sending/receiving messages inside Mesh network """

    PROCESS_INTERVAL = const(5)

    on_rcv_message = None
    on_rcv_ack = None

    def __init__(self, lock):
        #self.mesh = mesh
        self.lock = lock
        self.dict = {}
        self.rcv_dict = {}
        self.rcv_mess_new = None
        # maybe a periodic process function
        #self._timer = Timer.Alarm(self.periodic_cb, self.INTERVAL, periodic=True)

    def send_message(self, mac, payload, id, ts):
        """ send a new message """
        already = None
        try:
            already = self.dict[mac]
        except:
            pass
        if already is not None:
            print('old message deleted for %X' % mac)
        message = Message((mac, payload, id, ts))
        self.dict[mac] = message
        print("Added new message for %X: %s" % (mac, payload))
        return True

    def add_rcv_message(self, message):
        """ received a new message """
        message.ts = time.time()
        self.rcv_dict[message.mac] = message
        self.rcv_mess_new = message

        if self.on_rcv_message:
            self.on_rcv_message(message)

        return True

    def rcv_ack(self, data):
        """ just received an ACK for a previously sent message """
        message = Message()
        message.unpack_ack(data)

        # check if message was really in send buffer
        if message.mac in self.dict:
            self.dict[message.mac].state = Message.MESS_STATE_ACK

            if self.on_rcv_ack:
                self.on_rcv_ack(message)
        else:
            print(message.mac, self.dict)
        pass

    def mesage_was_ack(self, mac, id):
        """ return True/False if a message was ACK """
        done = False
        try:
            message = self.dict[mac]
            if id == message.id:
                if message.state == Message.MESS_STATE_ACK:
                    done = True
        except:
            pass
        print("ACK? mac %x, id %d => %d" % (mac, id, done))
        return done

    def get_rcv_message(self):
        """ returns first message that was received, None if none received """
        if len(self.rcv_dict) == 0:
            return None

        # get first message
        (mac, mess) = list(self.rcv_dict.items())[0]
        return (mac, mess.id, mess.ts, mess.payload)


class Message:

    PACK_MESSAGE = '!QHH'  # mac, id, payload size, and payload(char[])
    PACK_MESSAGE_ACK = '!QH'  # mac, id

    #MESS_STATE_INIT = const(1)
    MESS_STATE_IP_PENDING = const(2)
    MESS_STATE_SENT = const(3)
    MESS_STATE_ACK = const(4)

    """ class that holds a message and its properties """

    def __init__(self, data=None):
        self.local_ts = time.time()
        self.ip = None
        self.last_tx_ts = 0

        if data is None:
            return

        datatype = str(type(data))
        if datatype == "<class 'tuple'>":
            self._init_tuple(data)
        elif datatype == "<class 'bytes'>":
            self._init_bytes(data)
        # limit id to 2B
        self.id = self.id & 0xFFFF

    def _init_tuple(self, data):
        # (mac, payload, id, ts)
        (self.mac, self.payload, self.id, self.ts) = data
        self.state = MESS_STATE_IP_PENDING
        return

    def _init_bytes(self, data):
        #print('NeighborData._init_bytes %s'%str(data))
        self.mac, self.id, n = unpack(self.PACK_MESSAGE, data)
        self.payload = unpack('!' + str(n) + 's',
                              data[calcsize(self.PACK_MESSAGE):])
        return

    def pack(self, sender_mac):
        n = len(self.payload)
        data = pack(self.PACK_MESSAGE, sender_mac, self.id, n)
        data = data + pack('!' + str(n) + 's', self.payload)
        return data

    def pack_ack(self, sender_mac):
        data = pack(self.PACK_MESSAGE_ACK, sender_mac, self.id)
        return data

    def unpack_ack(self, data):
        (self.mac, self.id) = unpack(self.PACK_MESSAGE_ACK, data)
        pass
