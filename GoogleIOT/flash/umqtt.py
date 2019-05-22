#!/usr/bin/env python
#
# Copyright (c) 2019, Pycom Limited.
#
# This software is licensed under the GNU GPL version 3 or any
# later version, with permitted additional terms. For more information
# see the Pycom Licence v1.0 document supplied with this file, or
# available at https://www.pycom.io/opensource/licensing
#

'''umqtt is a simple MQTT client for MicroPython.
   Original code: https://github.com/micropython/micropython-lib/tree/master/umqtt.simple'''
import time
import os
import usocket as socket
import ustruct as struct
from ubinascii import hexlify


class MQTTException(Exception):
    pass


class MQTTClient:

    def __init__(self, client_id, server, port=0, user=None, password=None, keepalive=0,
                 ssl=False, ssl_params={}):
        if port == 0:
            port = 8883 if ssl else 1883
        self.client_id = client_id
        self.sock = None
        self.server = server
        self.addr = socket.getaddrinfo(server, port)[0][-1]
        self.ssl = ssl
        self.ssl_params = ssl_params
        self.pid = 0
        self.cb = None
        self.user = user
        self.pswd = password
        self.keepalive = keepalive
        self.lastWill_topic = None
        self.lastWill_msg = None
        self.lastWill_qos = 0
        self.lastWill_retain = False

    def _send_str(self, s):
        self.sock.write(struct.pack("!H", len(s)))
        self.sock.write(s)

    def _recv_len(self):
        n = 0
        sh = 0
        while 1:
            b = self.sock.read(1)[0]
            n |= (b & 0x7f) << sh
            if not b & 0x80:
                return n
            sh += 7

    def set_callback(self, f):
        self.cb = f

    def set_last_will(self, topic, msg, retain=False, qos=0):
        assert 0 <= qos <= 2
        assert topic
        self.lastWill_topic = topic
        self.lastWill_msg = msg
        self.lastWill_qos = qos
        self.lastWill_retain = retain

    def connect(self, clean_session=True):
        if (self.sock):
            # https://pycomiot.atlassian.net/browse/PB-358
            try:
                self.sock.send('') # can send == closeable
                self.sock.close()
            except Exception as e:
                self.sock = None    # socket is not closable
                import gc
                gc.collect()

        self.sock = socket.socket()
        self.sock.connect(self.addr)
        if self.ssl == True:
            import ussl
            pssl ={}
            if self.ssl_params  is not None and self.ssl_params.get('ca_certs') is not None:
                try:
                    os.stat(self.ssl_params.get('ca_certs'))
                    pssl["cert_reqs"] = ussl.CERT_REQUIRED
                    pssl["ca_certs"] = self.ssl_params.get('ca_certs')
                    if self.ssl_params.get('keyfile') is not None:
                        pssl["keyfile"] = self.ssl_params.get('keyfile')
                    if self.ssl_params.get('certfile') is not None:
                        pssl["certfile"] = self.ssl_params.get('certfile')
                except Exception as e:
                    print(e)
                    print("WARNING:TLS certificate validation for MQTT will be disabled",self.ssl_params.get('ca_file'), " is missing")

            else:
                print("WARNING: consider enabling TSL certificate validation for MQTT")
            # todo check the file if params and print error
            # os.stat(self.ssl_params.get('keyfile'))
            # os.stat(self.ssl_params.get('certfile'))
            self.sock = ussl.wrap_socket(self.sock, **pssl)
        else:
            print("WARNING: consider enabling TLS for MQTT")
        premsg = bytearray(b"\x10\0\0\0\0\0")
        msg = bytearray(b"\x04MQTT\x04\x02\0\0")

        size = 10 + 2 + len(self.client_id)
        msg[6] = clean_session << 1
        if self.user is not None:
            size += 2 + len(self.user) + 2 + len(self.pswd)
            msg[6] |= 0xC0
        if self.keepalive:
            assert self.keepalive < 65536
            msg[7] |= self.keepalive >> 8
            msg[8] |= self.keepalive & 0x00FF
        if self.lastWill_topic:
            size += 2 + len(self.lastWill_topic) + 2 + len(self.lastWill_msg)
            msg[6] |= 0x4 | (self.lastWill_qos & 0x1) << 3 | (self.lastWill_qos & 0x2) << 3
            msg[6] |= self.lastWill_retain << 5

        i = 1
        while size > 0x7f:
            premsg[i] = (size & 0x7f) | 0x80
            size >>= 7
            i += 1
        premsg[i] = size

        self.sock.write(premsg, i + 2)
        self.sock.write(msg)
        self._send_str(self.client_id)

        if self.lastWill_topic:
            self._send_str(self.lastWill_topic)
            self._send_str(self.lastWill_msg)

        if self.user is not None:
            self._send_str(self.user)
            self._send_str(self.pswd)

        resp = self.sock.read(4)
        if len(resp) == 0:
            print("[MQTT] ERR: server closed connection.")
            return
        assert resp[0] == 0x20 and resp[1] == 0x02
        if resp[3] != 0:
            raise MQTTException(resp[3])
        print("[MQTT] %s OK!" % self.server)
        return resp[2] & 1

    def disconnect(self):
        self.sock.write(b"\xe0\0")
        self.sock.close()

    def ping(self):
        self.sock.write(b"\xc0\0")

    def publish(self, topic, msg, retain=False, qos=0):
        pkt = bytearray(b"\x30\0\0\0")
        pkt[0] |= qos << 1 | retain
        size = 2 + len(topic) + len(msg)
        if qos > 0:
            size += 2
        assert size < 2097152
        i = 1
        while size > 0x7f:
            pkt[i] = (size & 0x7f) | 0x80
            size >>= 7
            i += 1
        pkt[i] = size
        # print('publish', hex(len(pkt)), hexlify(pkt).decode('ascii'))
        self.sock.write(pkt, i + 1)
        self._send_str(topic)
        if qos > 0:
            self.pid += 1
            pid = self.pid
            struct.pack_into("!H", pkt, 0, pid)
            self.sock.write(pkt, 2)
        self.sock.write(msg)

        if qos == 1:
            while 1:
                op = self.wait_msg()
                if op == 0x40:
                    size = self.sock.read(1)
                    assert size == b"\x02"
                    rcv_pid = self.sock.read(2)
                    rcv_pid = rcv_pid[0] << 8 | rcv_pid[1]
                    if pid == rcv_pid:
                        return
        elif qos == 2:
            assert 0

    def subscribe(self, topic, qos=0):
        assert self.cb is not None, "Subscribe callback is not set"
        pkt = bytearray(b"\x82\0\0\0")
        self.pid += 1
        struct.pack_into("!BH", pkt, 1, 2 + 2 + len(topic) + 1, self.pid)
        # print('subscribe', hex(len(pkt)), hexlify(pkt).decode('ascii'))
        self.sock.write(pkt)
        self._send_str(topic)
        self.sock.write(qos.to_bytes(1, "little"))
        while 1:
            op = self.wait_msg()
            if op == 0x90:
                resp = self.sock.read(4)
                # print('Response subscribe', hexlify(resp).decode('ascii'))
                assert resp[1] == pkt[2] and resp[2] == pkt[3]
                if resp[3] == 0x80:
                    raise MQTTException(resp[3])
                return

    # Wait for a single incoming MQTT message and process it.
    # Subscribed messages are delivered to a callback previously
    # set by .set_callback() method. Other (internal) MQTT
    # messages processed internally.
    def wait_msg(self):
        res = self.sock.read(1)
        self.sock.setblocking(True)
        if res is None:
            return None
        if res == b"":
            # other tls empty response happens ...
            # raise OSError(-1)
            return
        if res == b"\xd0":  # PING RESPONCE
            size = self.sock.read(1)[0]
            assert size == 0
            return None
        op = res[0]
        if op & 0xf0 != 0x30:
            return op
        size = self._recv_len()
        topic_len = self.sock.read(2)
        topic_len = (topic_len[0] << 8) | topic_len[1]
        topic = self.sock.read(topic_len)
        size -= topic_len + 2
        if op & 6:
            pid = self.sock.read(2)
            pid = pid[0] << 8 | pid[1]
            size -= 2
        msg = self.sock.read(size)
        self.cb(topic, msg)
        if op & 6 == 2:
            pkt = bytearray(b"\x40\x02\0\0")
            struct.pack_into("!H", pkt, 2, pid)
            self.sock.write(pkt)
        elif op & 6 == 4:
            assert 0

    # Checks whether a pending message from server is available.
    # If not, returns immediately with None. Otherwise, does
    # the same processing as wait_msg.
    def check_msg(self):
        self.sock.setblocking(False)
        return self.wait_msg()
