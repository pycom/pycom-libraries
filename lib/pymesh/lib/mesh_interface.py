
# Copyright (c) 2019, Pycom Limited.
#
# This software is licensed under the GNU GPL version 3 or any
# later version, with permitted additional terms. For more information
# see the Pycom Licence v1.0 document supplied with this file, or
# available at https://www.pycom.io/opensource/licensing

import time
from machine import Timer
#import _thread

from mesh_internal import MeshInternal
from statistics import Statistics

__version__ = '3'
"""
* added file send/receive debug

__version__ = '2'
* add sending messages

__version__ = '1'
* initial version, lock and get_mesh_members(), get_mesh_pairs
"""

class MeshInterface:
    """ Class for Mesh interface,
        all modules that uses Mesh should call only this class methods """

    INTERVAL = const(10)

    def __init__(self, meshaging, lock):
        self.lock = lock #_thread.allocate_lock()
        self.meshaging = meshaging
        self.mesh = MeshInternal(self.meshaging)
        self.sleep_function = None
        self.single_leader_ts = 0

        self.statistics = Statistics(self.meshaging)
        self._timer = Timer.Alarm(self.periodic_cb, self.INTERVAL, periodic=True)

        # just run this ASAP
        self.periodic_cb(None)

        pass

    def periodic_cb(self, alarm):
        # wait lock forever
        if self.lock.acquire():
            print("============ MESH THREAD >>>>>>>>>>> ")
            t0 = time.ticks_ms()

            self.mesh.process()
            if self.mesh.is_connected():
                self.statistics.process()
                self.mesh.process_messages()

            # if Single Leader for 3 mins should reset
            if self.mesh.mesh.state == self.mesh.mesh.STATE_LEADER and self.mesh.mesh.mesh.single():
                if self.single_leader_ts == 0:
                    # first time Single Leader, record time
                    self.single_leader_ts = time.time()
                print("Single Leader", self.mesh.mesh.state, self.mesh.mesh.mesh.single(),
                    time.time() - self.single_leader_ts)

                if time.time() - self.single_leader_ts > 180:
                    print("Single Leader, just reset")
                    if self.sleep_function:
                        self.sleep_function(1)
            else:
                # print("Not Single Leader", self.mesh.mesh.state, self.mesh.mesh.mesh.single())
                self.single_leader_ts = 0

            self.lock.release()

            print(">>>>>>>>>>> DONE MESH THREAD ============ %d\n"%(time.ticks_ms() - t0))

        pass

    def timer_kill(self):
        # with self.lock:
        self._timer.cancel()

    def get_mesh_mac_list(self):
        mac_list = list()
        if self.lock.acquire():
            # mac_list = list(self.mesh.get_all_macs_set())
            # mac_list.sort()
            mac_list = {0:list(self.mesh.get_all_macs_set())}
            self.lock.release()
        print("get_mesh_mac_list:", str(mac_list))
        return mac_list

    def get_mesh_pairs(self):
        mesh_pairs = []
        if self.lock.acquire():
            mesh_pairs = self.mesh.get_mesh_pairs()
            self.lock.release()
        #print("get_mesh_pairs: %s"%str(mesh_pairs))
        return mesh_pairs

    def set_gps(self, lng, lat):
        with open('/flash/gps', 'w') as fh:
            fh.write('%d;%d'.format(lng, lat))

    def is_connected(self):
        is_connected = None
        if self.lock.acquire():
            is_connected = self.mesh.is_connected()
            self.lock.release()
        return is_connected

    def ip(self):
        ip = None
        if self.lock.acquire():
            ip = self.mesh.mesh.mesh.ipaddr()
            self.lock.release()
        return ip

    def get_node_info(self, mac_id):
        data = {}
        try:
            mac = int(mac_id)
        except:
            mac = self.mesh.MAC
            print("get_node_info own mac")
        if self.lock.acquire():
            data = self.mesh.node_info(mac)
            self.lock.release()
        return data

    def send_message(self, data):
        ## WARNING: is locking required for just adding
        ret = False

        # check input parameters
        try:
            mac = int(data['to'])
            msg_type = data.get('ty', 0) # text type, by default
            payload = data['b']
            id = int(data['id'])
            ts = int(data['ts'])
        except:
            print('send_message: wrong input params')
            return False

        if self.lock.acquire():
            print("Send message to %d, typ %d, load %s"%(mac, msg_type, payload))
            ret = self.meshaging.send_message(mac, msg_type, payload, id, ts)
            # send messages ASAP
            self.mesh.process_messages()
            self.lock.release()

        return ret

    def mesage_was_ack(self, mac, id):
        ret = False
        if self.lock.acquire():
            ret = self.meshaging.mesage_was_ack(mac, id)
            self.lock.release()
        #print("mesage_was_ack (%X, %d): %d"%(mac, id, ret))
        return ret

    def get_rcv_message(self):
        """ returns a message that was received, {} if none is received """
        message = None
        if self.lock.acquire():
            message = self.meshaging.get_rcv_message()
            self.lock.release()
            if message is not None:
                (mac, id, ts, payload) = message
                return {'from':mac,
                    'b':payload,
                    'id':id,
                    'ts':ts}
        return {}

    def statistics_start(self, data):
        """ starts to do statistics based on message send/ack """
        # data = {'mac':6, 'n':3, 't':30, 's1':10, 's2':30}
        try:
            # validate input params
            mac = int(data['mac'])
            num_mess = int(data['n'])
            timeout = int(data['t'])
        except:
            print("statistics_start failed")
            print(data)
            return 0
        if mac == self.mesh.MAC:
            data['mac'] = 2
        res = self.statistics.add_stat_mess(data)
        return res

    def statistics_get(self, id):
        res = self.statistics.status(id)
        print(res)
        return res
