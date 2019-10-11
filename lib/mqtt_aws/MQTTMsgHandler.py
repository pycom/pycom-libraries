import MQTTConst as mqttConst
import time
import socket
import ssl
import _thread
import select
import struct

class MsgHandler:

    def __init__(self, receive_callback, connect_helper):
        self._host = ""
        self._port = -1
        self._cafile = ""
        self._key = ""
        self._cert = ""
        self._sock = None
        self._output_queue_size=-1
        self._output_queue_dropbehavior=-1
        self._mqttOperationTimeout = 5
        self._connection_state = mqttConst.STATE_DISCONNECTED
        self._conn_state_mutex=_thread.allocate_lock()
        self._poll = select.poll()
        self._output_queue=[]
        self._out_packet_mutex=_thread.allocate_lock()
        _thread.stack_size(8192)
        _thread.start_new_thread(self._io_thread_func, ())
        self._recv_callback = receive_callback
        self._connect_helper = connect_helper
        self._pingSent=False
        self._ping_interval=20
        self._waiting_ping_resp=False
        self._ping_cutoff=3
        self._receive_timeout=3000
        self._draining_interval=2
        self._draining_cutoff=3
        self._shadow_cb_queue=[]
        self._shadow_cb_mutex=_thread.allocate_lock()

    def setOfflineQueueConfiguration(self, queueSize, dropBehavior):
        self._output_queue_size = queueSize
        self._output_queue_dropbehavior = dropBehavior

    def setCredentials(self, srcCAFile, srcKey, srcCert):
        self._cafile = srcCAFile
        self._key = srcKey
        self._cert = srcCert

    def setEndpoint(self, srcHost, srcPort):
        self._host = srcHost
        self._port = srcPort

    def setOperationTimeout(self, timeout):
        self._mqttOperationTimeout=timeout

    def setDrainingInterval(self, srcDrainingIntervalSecond):
        self._draining_interval=srcDrainingIntervalSecond

    def insertShadowCallback(self, callback, payload, status, token):
        self._shadow_cb_mutex.acquire()
        self._shadow_cb_queue.append((callback, payload, status, token))
        self._shadow_cb_mutex.release()

    def _callShadowCallback(self):
        self._shadow_cb_mutex.acquire()
        if len(self._shadow_cb_queue) > 0:
            cbObj = self._shadow_cb_queue.pop(0)
            cbObj[0](cbObj[1],cbObj[2], cbObj[3])
        self._shadow_cb_mutex.release()

    def createSocketConnection(self):
        self._conn_state_mutex.acquire()
        self._connection_state = mqttConst.STATE_CONNECTING
        self._conn_state_mutex.release()
        try:
            if self._sock:
                self._poll.unregister(self._sock)
                self._sock.close()
                self._sock = None

            self._sock = socket.socket()
            self._sock.settimeout(30)
            if self._cafile:
                self._sock = ssl.wrap_socket(
                    self._sock,
                    certfile=self._cert,
                    keyfile=self._key,
                    ca_certs=self._cafile,
                    cert_reqs=ssl.CERT_REQUIRED)

            self._sock.connect(socket.getaddrinfo(self._host, self._port)[0][-1])
            self._poll.register(self._sock, select.POLLIN)
        except socket.error as err:
            print("Socket create error: {0}".format(err))

            self._conn_state_mutex.acquire()
            self._connection_state = mqttConst.STATE_DISCONNECTED
            self._conn_state_mutex.release()

            return False

        return True

    def disconnect(self):
        if self._sock:
            self._sock.close()
            self._sock = None

    def isConnected(self):
        connected=False
        self._conn_state_mutex.acquire()
        if self._connection_state == mqttConst.STATE_CONNECTED:
            connected = True
        self._conn_state_mutex.release()

        return connected

    def setConnectionState(self, state):
        self._conn_state_mutex.acquire()
        self._connection_state = state
        self._conn_state_mutex.release()

    def _drop_message(self):
        if self._output_queue_size == -1:
            return False
        elif (self._output_queue_size == 0) and (self._connection_state == mqttConst.STATE_CONNECTED):
            return False
        else:
            return True if len(self._output_queue) >= self._output_queue_size else False

    def push_on_send_queue(self, packet):
        if self._drop_message():
            if self._output_queue_dropbehavior == mqttConst.DROP_OLDEST:
                self._out_packet_mutex.acquire()
                if self._out_packet_mutex.locked():
                    self._output_queue.pop(0)
                self._out_packet_mutex.release()
            else:
                return False

        self._out_packet_mutex.acquire()
        if self._out_packet_mutex.locked():
            self._output_queue.append(packet)
        self._out_packet_mutex.release()

        return True

    def priority_send(self, packet):
        msg_sent = False
        self._out_packet_mutex.acquire()
        msg_sent = self._send_packet(packet)
        self._out_packet_mutex.release()

        return msg_sent

    def _receive_packet(self):
        try:
            if not self._poll.poll(self._receive_timeout):
                return False
        except Exception as err:
            print("Poll error: {0}".format(err))
            return False

        # Read message type
        try:
            self._sock.setblocking(False)
            msg_type = self._sock.recv(1)
        except socket.error as err:
            print("Socket receive error: {0}".format(err))
            return False
        else:
            if len(msg_type) == 0:
                return False
            msg_type = struct.unpack("!B", msg_type)[0]
            self._sock.setblocking(True)

        # Read payload length
        multiplier = 1
        bytes_read = 0
        bytes_remaining = 0
        while True:
            try:
                if self._sock:
                    byte = self._sock.recv(1)
            except socket.error as err:
                print("Socket receive error: {0}".format(err))
                return False
            else:
                bytes_read = bytes_read + 1
                if bytes_read > 4:
                    return False

                byte = struct.unpack("!B", byte)[0]
                bytes_remaining +=  (byte & 127) * multiplier
                multiplier += 128

            if (byte & 128) == 0:
                break

        # Read payload
        try:
            if self._sock:
                if bytes_remaining > 0:
                    payload = self._sock.recv(bytes_remaining)
                else:
                    payload = b''
        except socket.error as err:
                print("Socket receive error: {0}".format(err))
                return False

        return self._recv_callback(msg_type, payload)

    def _send_pingreq(self):
        pkt = struct.pack('!BB', mqttConst.MSG_PINGREQ, 0)
        return self.priority_send(pkt)

    def setPingFlag(self, flag):
        self._pingSent=flag

    def _send_packet(self, packet):
        written = -1
        try:
            if self._sock:
                written = self._sock.write(packet)
                if(written == None):
                    written = -1
                else:
                    print('Packet sent. (Length: %d)' % written)
        except socket.error as err:
            print('Socket send error {0}'.format(err))
            return False

        return True if len(packet) == written else False

    def _verify_connection_state(self):
        elapsed = time.time() - self._start_time
        if not self._waiting_ping_resp and elapsed > self._ping_interval:
            if self._connection_state == mqttConst.STATE_CONNECTED:
                self._pingSent=False
                self._send_pingreq()
                self._waiting_ping_resp=True
            elif self._connection_state == mqttConst.STATE_DISCONNECTED:
                self._connect_helper()

            self._start_time = time.time()
        elif self._waiting_ping_resp and (self._connection_state == mqttConst.STATE_CONNECTED or elapsed > self._mqttOperationTimeout):
            if not self._pingSent:
                if self._ping_failures <= self._ping_cutoff:
                    self._ping_failures+=1
                else:
                    self._connect_helper()
            else:
                self._ping_failures=0

            self._start_time = time.time()
            self._waiting_ping_resp = False

    def _io_thread_func(self):
        time.sleep(5.0)

        self._start_time = time.time()
        self._ping_failures=0
        while True:

            self._verify_connection_state()

            self._out_packet_mutex.acquire()
            if self._ping_failures == 0:
                if self._out_packet_mutex.locked() and len(self._output_queue) > 0:
                    packet=self._output_queue[0]
                    if self._send_packet(packet):
                        self._output_queue.pop(0)
            self._out_packet_mutex.release()

            self._receive_packet()
            self._callShadowCallback()

            if len(self._output_queue) >= self._draining_cutoff:
                time.sleep(self._draining_interval)