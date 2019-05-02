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
import _thread
from cli import Cli

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
        return { 'res': 'demo_fn' }

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


    def get_node_info(self, mac_id = ' '):
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
        node_info = mesh.get_node_info(mac_id)
        return node_info

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

    def send_image(self, data):
        """ sends an image
            return True if there is buffer to store it (to be sent)"""
        print("Send Image ---------------------->>>>>>>> ", data)
        start = 0
        filename = 'dog_2.jpg'
        to = 0
        # packsize = 500
        image = list()

        try:
            filename = data.get('fn', "image.jpg")
            start = int(data['start'])
            image = bytes(data['image'])
        except:
            print('parsing failed')
            return False

        print("Image chunk size: %d"%len(image))
        file_handling = "ab" # append, by default
        if start == 0:
            file_handling = "wb" # write/create new

        with open("/flash/" + filename, file_handling) as file:
            print("file open")
            file.write(image)
            print("file written")

        print("done")
        return True

    def stat_start(self, data):
        # do some statistics
        #data = {'mac':6, 'n':3, 't':30}
        res = self.mesh.statistics_start(data)
        print("rpc stat_start? ", res)
        return res

    def stat_status(self, data):
        print("rpc stat_status ", data)
        try:
            id = int(data)
        except:
            id = 0
        res = mesh.statistics_get(id)
        print("rpc stat_status id:"+ str(id) + ", res: " + str(res))
        return res

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

    msg = msgpack.packb(['notify', 'msg', message_data])
    rx_worker.put(msg)
    print(message_data['payload'])
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

kill_all = False
deepsleep_timeout = 0

watchdog = Watchdog(meshaging, mesh)

def deepsleep_now():
    """ prepare scripts for graceful exit, deepsleeps if case """
    mesh.timer_kill()
    watchdog.timer_kill()
    rx_worker.timer_kill()
    ble_comm.close()
    Gps.terminate()
    mesh.statistics.save_all()
    print('Cleanup code, all Alarms cb should be stopped')
    if deepsleep_timeout > 0:
        print('Going to deepsleep for %d seconds'%deepsleep_timeout)
        time.sleep(1)
        machine.deepsleep(deepsleep_timeout * 1000)

def deepsleep_init(timeout):
    """ initializes an deeppsleep sequence, that will be performed later """
    global deepsleep_timeout, kill_all
    deepsleep_timeout = timeout
    kill_all = True
    return

mesh.statistics.sleep_function = deepsleep_init
mesh.sleep_function = deepsleep_init

cli = Cli(mesh, rpc_handler, ble_comm)
cli.sleep = deepsleep_init

_thread.start_new_thread(cli.process, (1, 2))

try:
    while True:
        if kill_all:
            deepsleep_now()

        time.sleep(.1)
        pass

except KeyboardInterrupt:
    print('Got Ctrl-C')
except Exception as e:
    sys.print_exception(e)
finally:
    deepsleep_now()

