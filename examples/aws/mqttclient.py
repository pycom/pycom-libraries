import socket
import struct
import select
from binascii import hexlify

class MQTTException(Exception):
    pass

class MQTTClient:

    def __init__(self, client_id, server, port=1883, user=None, password=None):
        self.client_id = client_id.encode('utf8')
        self.sock = None
        self.addr = socket.getaddrinfo(server, port)[0][-1]
        self.pid = 0
        self.cb = None
        self.poll = select.poll()
        self.__will_message = None
        if user:
            self.__user = user.encode('utf8')
        else:
            self.__user = None
        self.__password = password

    def __encode_varlen_length(self, length):
        i = 0
        buff = bytearray()
        while 1:
            buff.append(length % 128)
            length = length // 128
            if length > 0:
                buff[i] = buff[i] | 0x80
                i += 1
            else:
                break

        return buff

    def __encode_16(self, x):
        return struct.pack("!H", x)

    def __pascal_string(self, s):
        return struct.pack("!H", len(s)) + s

    def __recv_varlen_length(self):
        m = 1
        val = 0
        while 1:
            b = self.sock.recv(1)[0]
            val += (b & 0x7F) * m
            m *= 128
            if m > 2097152: # 128 * 128 * 128
                raise MQTTException()
            if (b & 0x80) == 0:
                break
        return val

    def set_callback(self, f):
        self.cb = f

    def set_will(self, will_topic, will_message, will_qos=0, will_retain=0):
        if will_topic:
            self.__will_topic = will_topic.encode('utf8')
        self.__will_message = will_message
        self.__will_qos = will_qos
        self.__will_retain = will_retain

    def connect(self, clean_session=True, ssl=False, certfile=None, keyfile=None, ca_certs=None):
        try:
            self.poll.unregister(self.sock)
        except:
            pass
        self.sock = socket.socket()

        if ssl:
            import ssl
            self.sock = ssl.wrap_socket(self.sock, certfile=certfile, keyfile=keyfile, ca_certs=ca_certs, cert_reqs=ssl.CERT_REQUIRED)

        self.sock.connect(self.addr)
        self.poll.register(self.sock, select.POLLIN)

        pkt_len = (12 + len(self.client_id) + # 10 + 2 + len(client_id)
                    (2 + len(self.__user) if self.__user else 0) +
                    (2 + len(self.__password) if self.__password else 0))

        flags = (0x80 if self.__user else 0x00) | (0x40 if self.__password else 0x00) | (0x02 if clean_session else 0x00)

        if self.__will_message:
            flags |= (self.__will_retain << 3 | self.__will_qos << 1 | 1) << 2
            pkt_len += 4 + len(self.__will_topic) + len(self.__will_message)

        pkt = bytearray([0x10]) # connect
        pkt.extend(self.__encode_varlen_length(pkt_len)) # len of the remaining
        pkt.extend(b'\x00\x04MQTT\x04') # len of "MQTT" (16 bits), protocol name, and protocol version
        pkt.append(flags)
        pkt.extend(b'\x00\x00') # disable keepalive
        pkt.extend(self.__pascal_string(self.client_id))
        if self.__will_message:
            pkt.extend(self.__pascal_string(self.__will_topic))
            pkt.extend(self.__pascal_string(self.__will_message))
        if self.__user:
            pkt.extend(self.__pascal_string(self.__user))
        if self.__password:
            pkt.extend(self.__pascal_string(self.__password))

        self.sock.send(pkt)
        resp = self.sock.recv(4)
        assert resp[0] == 0x20 and resp[1] == 0x02
        if resp[3] != 0:
            raise MQTTException(resp[3])
        return resp[2] & 1

    def disconnect(self):
        self.sock.send(b"\xe0\0")
        self.sock.close()

    def ping(self):
        self.sock.send(b"\xc0\0")

    def publish(self, topic, msg, retain=False, qos=0, dup=0):
        topic = topic.encode('utf8')
        hdr = 0x30 | (dup << 3) | (qos << 1) | retain
        pkt_len = (2 + len(topic) +
                    (2 if qos else 0) +
                    (len(msg)))

        pkt = bytearray()
        pkt.append(hdr)
        pkt.extend(self.__encode_varlen_length(pkt_len)) # len of the remaining
        pkt.extend(self.__pascal_string(topic))
        if qos:
            self.pid += 1 #todo: I don't think this is the way to deal with the packet id
            pkt.extend(self.__encode_16(self.pid))

        self.sock.send(pkt)
        self.sock.send(msg)

        #todo: check next part of the code
        if qos == 1:
            while 1:
                rcv_pid = self.recv_pubconf(0)
                if pid == rcv_pid:
                    return
        elif qos == 2:
            assert 0
    def recv_pubconf(self, t):
        headers = [0x40, 0x50, 0x62, 0x70]
        header = headers[t]
        while 1:
            op = self.wait_msg()
            if op == header:
                sz = self.sock.recv(1)
                assert sz == b"\x02"
                return

    def subscribe(self, topic, qos=0):
        assert self.cb is not None, "Subscribe callback is not set"

        topic = topic.encode('utf8')
        pkt_len = 2 + 2 + len(topic) + 1 # packet identifier + len of topic (16 bits) + topic len + QOS

        self.pid += 1
        pkt = bytearray([0x82])
        pkt.extend(self.__encode_varlen_length(pkt_len)) # len of the remaining
        pkt.extend(self.__encode_16(self.pid))
        pkt.extend(self.__pascal_string(topic))
        pkt.append(qos)

        self.sock.send(pkt)
        resp = self.sock.recv(5)
        #print(resp)
        assert resp[0] == 0x90
        assert resp[2] == pkt[2] and resp[3] == pkt[3]
        if resp[4] == 0x80:
            raise MQTTException(resp[4])

    # Wait for a single incoming MQTT message and process it.
    # Subscribed messages are delivered to a callback previously
    # set by .set_callback() method. Other (internal) MQTT
    # messages processed internally.
    def wait_msg(self):
        res = self.sock.recv(1)
        self.sock.setblocking(True)
        if res is None or res == b"":
            return None
        #if res == b"":
        #    raise OSError(-1)
        if res == b"\xd0":  # PINGRESP
            sz = self.sock.recv(1)[0]
            assert sz == 0
            return None
        op = res[0]
        if op & 0xf0 != 0x30:
            return op
        sz = self.__recv_varlen_length()
        topic_len = self.sock.recv(2)
        topic_len = (topic_len[0] << 8) | topic_len[1]
        topic = self.sock.recv(topic_len)
        sz -= topic_len + 2
        if op & 6:
            pid = self.sock.recv(2)
            pid = pid[0] << 8 | pid[1]
            sz -= 2
        msg = self.sock.recv(sz)
        self.cb(topic, msg)
        if op & 6 == 2:
            pkt = bytearray(b"\x40\x02\0\0")
            struct.pack_into("!H", pkt, 2, pid)
            self.sock.send(pkt)
        elif op & 6 == 4:
            assert 0

    # Checks whether a pending message from server is available.
    # If not, returns immediately with None. Otherwise, does
    # the same processing as wait_msg.
    def check_msg(self):
        self.sock.setblocking(False)
        return self.wait_msg()
