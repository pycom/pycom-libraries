
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

    def send_message(self, mac, msg_type, payload, id, ts):
        """ send a new message """
        already = self.dict.get(mac, None)
        if already:
            print('old message deleted for %X' % mac)
        message = Message((mac, msg_type, payload, id, ts))
        self.dict[mac] = message
        print("Added new message for %X: %s" % (mac, str(payload)))
        
        return True

    def add_rcv_message(self, message):
        """ received a new message """
        message.ts = time.time()
        self.rcv_dict[message.mac] = message
        self.rcv_mess_new = message

        if message.payload == b'dog':#🐕':
            message.payload = 'Picture started receiving'
            print('Rcv mess about dog, so we start receiving picture')
        else:
            print('payload is not dog')

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

            # check if message was about picture sending, to start actual file sending
            mess = self.dict[message.mac]
            if mess.payload == 'dog':
                print('ACK from dog message, start picture sending')
                del self.dict[message.mac]
                self.send_message(message.mac, message.TYPE_IMAGE, 'dog.jpg', message.id, time.time())
                
                if self.on_rcv_message:
                    mess = Message((message.mac, message.TYPE_TEXT, 'Receiving the picture', message.id+1, time.time()))
                    self.on_rcv_message(mess)
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

    def file_transfer_done(self, rcv_data):
        message = Message(rcv_data)
        message.payload = 'Picture was received'
        print('Picture done receiving from %d', message.mac)
        message.id = message.id + 1
        if self.on_rcv_message:
            self.on_rcv_message(message)
        
        self.send_message(message.mac, message.TYPE_TEXT, 'Picture was received', message.id+1, time.time())
        
        pass

class Message:

    PACK_MESSAGE = '!QHH'  # mac, id, payload size, and payload(char[])
    PACK_MESSAGE_ACK = '!QH'  # mac, id

    #MESS_STATE_INIT = const(1)
    MESS_STATE_IP_PENDING = const(2)
    MESS_STATE_SENT = const(3)
    MESS_STATE_ACK = const(4)

    # type of message: TEXT or IMAGE
    TYPE_TEXT = const(0)
    TYPE_IMAGE = const(1)

    """ class that holds a message and its properties """

    def __init__(self, data=None):
        self.local_ts = time.time()
        self.ip = "0"
        self.last_tx_ts = 0
        self.type = TYPE_TEXT
        self.send_f = None
        self.ts = time.time()

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
        (self.mac, self.type, self.payload, self.id, self.ts) = data
        self.state = self.MESS_STATE_IP_PENDING
        if self.type == TYPE_IMAGE:
            self.send_f = Send_File(self.payload)
        return

    def _init_bytes(self, data):
        #print('NeighborData._init_bytes %s'%str(data))
        self.mac, self.id, n = unpack(self.PACK_MESSAGE, data)
        self.payload = data[calcsize(self.PACK_MESSAGE):]
        #self.payload = unpack('!' + str(n) + 's', data[calcsize(self.PACK_MESSAGE):])
        return

    def pack(self, sender_mac, answer):
        n = len(self.payload)
        data = pack(self.PACK_MESSAGE, sender_mac, self.id, n)
        if self.type == TYPE_IMAGE:
            if self.send_f:
                file_chunk = self.send_f.process(answer)
                if len(file_chunk) == 0:
                    self.state = MESS_STATE_ACK
                    data = None
                else:
                    data = data + file_chunk
        else:
            #data = data + pack('!' + str(n) + 's', self.payload)
            data = data + self.payload
        return data

    def pack_ack(self, sender_mac):
        data = pack(self.PACK_MESSAGE_ACK, sender_mac, self.id)
        return data

    def unpack_ack(self, data):
        (self.mac, self.id) = unpack(self.PACK_MESSAGE_ACK, data)
        pass

class Send_File:
    INIT = const(1)
    WAIT_ACK = const(2)
    DONE = const(3)

    RETRIES_MAX = const(3)

    def __init__(self, filename):
        self.packsize = 400 # packsize
        self.buffer = bytearray(self.packsize)
        self.mv = memoryview(self.buffer)
        #self.ip = 0 # ip
        self.chunk = 0
        self.filename = filename
        try:
            self.file = open(filename, "rb")
        except:
            print("File %s can't be opened !!!!"%filename)
            self.state = DONE
            return
        self.size = 0
        

        self.start = time.time()
        self.state = INIT

    def process(self, last_response):
        if self.state == INIT:
            self.chunk = self.file.readinto(self.buffer)
            self.state = WAIT_ACK
            self.retries = 0
            self.size = self.chunk
            self.start = time.time()

        elif self.state == WAIT_ACK:
            if last_response is not None:
                # got ACK, send next chunk
                self.chunk = self.file.readinto(self.buffer)
                self.size = self.size + self.chunk
                print("%d Bytes sent, time: %4d sec" % (self.size, time.time() - self.start))
                if self.chunk == 0:
                    self._end_transfer()

                self.retries = 0
            else:
                print("No answer, so retry?")
                if time.time() - self.last_ts < 5:
                    #if we just sent the retry, don't resend anything, still wait for answer
                    print("No retry, too soon")
                    return ''
                self.retries = self.retries + 1

            if self.retries > RETRIES_MAX:
                self._end_transfer()

        elif self.state == DONE:
            self.chunk = 0

        self.last_ts = time.time()
        return self.mv[:self.chunk]

    def _end_transfer(self):
        self.state = DONE
        print("Done sending %d B in %s sec"%(self.size, time.time() - self.start))
        self.file.close()
