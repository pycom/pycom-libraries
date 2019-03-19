VERSION = "1.0.0"

# Copyright (c) 2019, Pycom Limited.
#
# This software is licensed under the GNU GPL version 3 or any
# later version, with permitted additional terms. For more information
# see the Pycom Licence v1.0 document supplied with this file, or
# available at https://www.pycom.io/opensource/licensing

import time
import json
import pycom
import _thread
import sys
import select
import _thread
import machine
from machine import Timer
from machine import Pin

from network import Bluetooth

import msgpack
import ble

from mesh_interface import MeshInterface
from gps import Gps

from meshaging import Meshaging

class RXWorker:
    def __init__(self, ble_comm):
        self.HEADSIZE = 20
        self.INTERVAL = .1
        self.q = b''
        self.ble_comm = ble_comm
        self.chr = ble_comm.chr_rx
        self.call_cnt = 0

        # mutex for self.q usage
        self.q_lock = _thread.allocate_lock()

        self._timer = Timer.Alarm(self.interval_cb, self.INTERVAL, periodic=True)

    def put(self, bytes):
        with self.q_lock:
            self.q = self.q + bytes

            # chunks = [ self.q[i:i+self.HEADSIZE] for i in range(0, len(self.q), self.HEADSIZE) ]
            # for chunk in chunks:
            #     self.chr.value(chunk)

            #self.chr.value('')
        #self.chr.value(bytes)

    def interval_cb(self, alarm):
        self.call_cnt = self.call_cnt + 1
        if self.call_cnt >= 10:
            # print('%d: rx worker interval.... %d'%(time.time(), len(self.q)))
            self.call_cnt = 0

        if len(self.q) == 0:
            return

        if not self.ble_comm.status['connected']:
            #unpacker._buffer = bytearray([])
            with self.q_lock:
                self.q = b''
            return
        try:
            with self.q_lock:
                head = self.q[:self.HEADSIZE]
                tail = self.q[self.HEADSIZE:]
                self.q = tail
                #print('consuming {}, {}', head, tail)

            if self.chr and len(head) > 0:
                self.chr.value(head)
                #print('sending', list(head))
        except:
            pass

    def timer_kill(self):
        self._timer.cancel()

class TXWorker:
    def __init__(self, ble_comm):
        self.ble_comm = ble_comm
        self.chr = ble_comm.chr_tx
        self.last_value = b''
        self.on_write = lambda value : 1

        self.chr.callback(trigger=Bluetooth.CHAR_WRITE_EVENT | Bluetooth.CHAR_READ_EVENT, handler=self.cb_handler)

    def cb_handler(self, chr):
        events = chr.events()
        if  events & Bluetooth.CHAR_WRITE_EVENT:
            self.last_value = chr.value()
            #print("Write request with value = {}".format(self.last_value))

            self.on_write(self.last_value)
        else:
            #print('Read request on char 1')
            return self.last_value

class RPCHandler:
    def __init__(self, rx_worker, tx_worker, mesh, ble_comm):
        self.rx_worker = rx_worker
        self.tx_worker = tx_worker
        self.mesh = mesh
        self.unpacker = msgpack.Unpacker(raw=False)
        self.error = False
        ble_comm.unpacker_set(self.unpacker)

        tx_worker.on_write = self.feed

    def feed(self, message):
        #print('feeding (rpc)', message)
        self.unpacker.feed(message)
        try:
            [self.resolve(x) for x in self.unpacker]
        except Exception as e:
            sys.print_exception(e)
            print('error in unpacking... reset')
            self.unpacker._buffer = bytearray()
            self.error = True



    def resolve(self, obj):
        #print('resolving: ', obj)
        obj = list(obj)
        type = obj[0]

        if type == 'call':
            uuid = obj[1]
            fn_name = obj[2]
            args = obj[3]
            fn = getattr(self, fn_name)

            if not fn:
                print('fn {} not defined'.format(fn_name))
                return

            try:
                result = fn(*args)
                result = json.loads(json.dumps(result))
                print('calling RPC: {} - {}'.format(fn_name, result))

                message = msgpack.packb(['call_result', uuid, result])
            except Exception as e:
                print('could not send result: {}'.format(result))
                return


            #print('result', result)
            #print('message', message)
            self.rx_worker.put(message)

    def demo_fn(self, *args):
        global last_mesh_pairs, last_mesh_members
        return {
            'p': last_mesh_pairs,
            'm': last_mesh_members,
        }

    def demo_echo_fn(self, *args):
        return args

    def mesh_is_connected(self):
        # True if Node is connected to Mesh; False otherwise
        is_connected = self.mesh.is_connected()
        return is_connected

    def mesh_ip(self):
        # get IP RLOC16 in string
        ip = self.mesh.ip()
        return ip

    def set_gps(self, lng, lat):
        print('settings gps!')
        Gps.set_location(lat, lng)
        # with open('/flash/gps', 'w') as fh:
        #     fh.write('{};{}'.format(lng, lat))

    def get_mesh_mac_list(self):
        """  returns list of distinct MAC address that are in this mesh network
        [mac1, mac2, mac 3] """
        last_mesh_mac_list = self.mesh.get_mesh_mac_list()
        return last_mesh_mac_list

    def get_mesh_pairs(self, *args):
        """  returns list of pairs that is a mesh connection
        [
            ('mac1', 'mac2', rssi),
            ('mac1', 'mac3', rssi),
            #...
        ] """
        last_mesh_pairs = self.mesh.get_mesh_pairs()
        return last_mesh_pairs


    def get_node_info(self, mac_id):
        global last_mesh_node_info
        """ Returns the debug info for a specified mac address
        takes max 10 sec
        {
            'ip': 4c00,   # last 2bytes from the ip v6 RLOC16 address
            'r': 3,    # not_connected:0 | child:1 | leader:2 | router:3
            'a': 100,  # age[sec], time since last info about this node
            'nn' : 20 # neighbours number
            'nei': {  # neighbours enumerated, if any
            (mac, ip, role, rssi, age),
            (mac, ip, role, rssi, age)
            }
            'l': { # location, if available
            'lng': 7,
            'lat': 20,
            },
            'b' : { # BLE infos
            'a': 100    # age, seconds since last ping with that device, None if properly disconnected
            'id': '<UUID>' # 16byte
            'n': '',           # name, max. 16 chars
            }
        } """
        #res = self.mesh.get_node_info(mac_list[0])
        try:
            mac = int(mac_id)
            node_info = last_mesh_node_info.get(mac, {})
            if len(node_info) == 0:
                node_info = mesh.get_node_info(mac)
            return node_info
        except:
            return {}


    def send_message(self, data):
        """ sends a message with id, to m(MAC)
            return True if there is buffer to store it (to be sent)"""
        """ data is dictionary data = {
            'to': 0x5,
            'b': 'text',
            'id': 12345,
            'ts': 123123123,
        }"""
        print("%d: Send Msg ---------------------->>>>>>>> "%time.ticks_ms())
        return self.mesh.send_message(data)

    def send_message_was_sent(self, mac, msg_id):
        """ checks for ACK received for msg_id
            returns True if message was delivered to last node connected to BLE mobile """
        error = False
        try:
            mac_int = int(mac)
            msg_id_int = int(msg_id)
        except:
            error = True
        if error:
            return False
        # mesh.mesage_was_ack(5, 12345)
        return self.mesh.mesage_was_ack(mac, msg_id)

    def receive_message(self):
        """
        return {
              'b': 'text',
              'from': 'ble_device_id',
              'ts': 123123123,
              'id': '<uuid>',
            } """
        return self.mesh.get_rcv_message()

class Watchdog:
    def __init__(self, meshaging, mesh):
        self.INTERVAL = 10
        self.meshaging = meshaging
        self.mesh = mesh        
        self._timer = Timer.Alarm(self.interval_cb, self.INTERVAL, periodic=True)

    def timer_kill(self):
        self._timer.cancel()

    def interval_cb(self, *args, **kwargs):
        global rpc_handler, rx_worker, tx_worker, mesh, ble_comm

        #print("watchdog!")

        if rpc_handler.error:
            rpc_handler = RPCHandler(rx_worker, tx_worker, mesh, ble_comm)
            print("**********  Restarted RPC Handler")


################################################################################
# Main code

pycom.heartbeat(False)
mesh_lock = _thread.allocate_lock()
meshaging = Meshaging(mesh_lock)
mesh = MeshInterface(meshaging, mesh_lock)

def on_rcv_message(message):
    message_data = {
        'mac' : message.mac,
        'payload' : message.payload,
        'ts' : message.ts,
        'id' : message.id,
    }

    if message.payload == '🐕':
        pycom.rgbled(0xff00ff)

    msg = msgpack.packb(['notify', 'msg', message_data])
    rx_worker.put(msg)
    print("%d =================  RECEIVED :) :) :) "%time.ticks_ms())
mesh.meshaging.on_rcv_message = on_rcv_message

def on_rcv_ack(message):
    message_data = {
        'id' : message.id,
    }

    msg = msgpack.packb(['notify', 'msg-ack', message_data])
    rx_worker.put(msg)
    print("%d =================  ACK RECEIVED :) :) :) "%time.ticks_ms())
mesh.meshaging.on_rcv_ack = on_rcv_ack

ble_comm = ble.BleCommunication(mesh.mesh.mesh.MAC)

def ble_on_disconnect():
    rpc_handler = RPCHandler(rx_worker, tx_worker, mesh, ble_comm)
ble_comm.on_disconnect = ble_on_disconnect

rx_worker = RXWorker(ble_comm)
tx_worker = TXWorker(ble_comm)

rpc_handler = RPCHandler(rx_worker, tx_worker, mesh, ble_comm)

Gps.init_static()

print("done !")

last_mesh_pairs = []
last_mesh_mac_list = []
last_mesh_node_info = {}

watchdog = Watchdog(meshaging, mesh)

try:
    while True:

        # print("============ MAIN LOOP >>>>>>>>>>>")
        # t0 = time.ticks_ms()
        # mesh_mac_list = mesh.get_mesh_mac_list()
        # if len(mesh_mac_list) > 0:
        #     last_mesh_mac_list = mesh_mac_list
        # print('mesh_mac_list ', json.dumps(last_mesh_mac_list))

        # mesh_pairs = mesh.get_mesh_pairs()
        # if len(mesh_pairs) > 0:
        #     last_mesh_pairs = mesh_pairs
        # print('last_mesh_pairs', json.dumps(last_mesh_pairs))

        # # ask node_info for each from the mac list
        # for mac in mesh_mac_list:
        #     node_info = mesh.get_node_info(mac)
        #     if len(node_info) > 0:
        #         last_mesh_node_info[mac] = node_info
        # print('last_mesh_node_info', json.dumps(last_mesh_node_info))
        # print(">>>>>>>>>>> DONE MAIN LOOP ============ %d\n"%(time.ticks_ms() - t0))

        # time.sleep(15)

        #todo: if RPC parsing/execution error, then


        cmd = input('>')

        if cmd == 'rb':
            print('resetting unpacker buffer')
            rpc_handler = RPCHandler(rx_worker, tx_worker, mesh, ble_comm)

        elif cmd == 'mac':
            print(mesh.mesh.mesh.MAC)

        elif cmd == 'mml':
            #t0 = time.ticks_ms()
            mesh_mac_list = mesh.get_mesh_mac_list()
            if len(mesh_mac_list) > 0:
                last_mesh_mac_list = mesh_mac_list
            print('mesh_mac_list ', json.dumps(last_mesh_mac_list))

        elif cmd == 'mni':
            for mac in last_mesh_mac_list:
                node_info = mesh.get_node_info(mac)
                time.sleep(.5)
                if len(node_info) > 0:
                    last_mesh_node_info[mac] = node_info
            print('last_mesh_node_info', json.dumps(last_mesh_node_info))
            #print(">>>>>>>>>>> DONE MAIN LOOP ============ %d\n"%(time.ticks_ms() - t0))

        elif cmd == 'mp':
            mesh_pairs = mesh.get_mesh_pairs()
            if len(mesh_pairs) > 0:
                last_mesh_pairs = mesh_pairs
            print('last_mesh_pairs', json.dumps(last_mesh_pairs))

        elif cmd == 's':
            to = int(input('(to)<'))
            txt = input('(txt)<')
            data = {
                'to': to,
                'b': txt or 'Hello World!',
                'id': 12345,
                'ts': int(time.time()),
            }
            print(rpc_handler.send_message(data))

        elif cmd == 'ws':
            to = int(input('(to)<'))
            print(rpc_handler.send_message_was_sent(to, 12345))

        elif cmd == 'rm':
            print(rpc_handler.receive_message())

        elif cmd == 'gg':
            print("Gps:", (Gps.lat, Gps.lon))

        elif cmd == 'gs':
            lat = float(input('(lat)<'))
            lon = float(input('(lon)<'))
            Gps.set_location(lat, lon)
            print("Gps:", (Gps.lat, Gps.lon))

        elif cmd == 'f':
            try:
                to = int(input('(MAC to)<'))
                packsize = int(input('(packsize)<'))
                filename = input('(filename, Enter for dog.jpg)<')
                if len(filename) == 0:
                    filename = 'dog.jpg'
                ip = mesh.mesh.mesh.ip_mac_unique(to)
            except:
                continue
            mesh.send_file(ip, packsize, filename)

        elif cmd == 'exit':
            print('exit!')
            break

        elif cmd == "rst":
            print("Mesh Reset... ")
            mesh.mesh.mesh.mesh.deinit()
            #mesh.mesh.lora.Mesh()
            machine.reset()
        pass

except KeyboardInterrupt:
    print('Got Ctrl-C')
except Exception as e:
    sys.print_exception(e)
finally:
    mesh.timer_kill()
    watchdog.timer_kill()
    rx_worker.timer_kill()
    ble_comm.close()
    Gps.terminate()
    print('Cleanup code, all Alarms cb should be stopped')
