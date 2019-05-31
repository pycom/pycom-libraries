#!/usr/bin/env python
#
# Copyright (c) 2019, Pycom Limited.
#
# This software is licensed under the GNU GPL version 3 or any
# later version, with permitted additional terms. For more information
# see the Pycom Licence v1.0 document supplied with this file, or
# available at https://www.pycom.io/opensource/licensing
#

from distutils.version import LooseVersion
from LoraServer import LoraServerClient
from groupUpdater import updateHandler
import threading
import json
import base64
import os
import time
import config


class OTAHandler:

    MSG_HEADER = b'$OTA'
    MSG_TAIL = b'*'
    MSG_END = b'<!EOF>'
    
    FULL_UPDATE = b'F'
    DIFF_UPDATE = b'D'
    NO_UPDATE = b'N'

    UPDATE_INFO_MSG = 1
    UPDATE_INFO_REPLY = 2

    MULTICAST_KEY_REQ = 3
    MULTICAST_KEY_REPLY = 4

    LISTENING_MSG = 5
    LISTENING_REPLY = 6

    UPDATE_TYPE_FNAME = 7
    UPDATE_TYPE_PATCH = 8
    UPDATE_TYPE_CHECKSUM = 9

    DELETE_FILE_MSG = 10
    MANIFEST_MSG = 11

    def __init__(self):
        self._exit = False
        self.p_client = None
        self._latest_version = '0.0.0'
        self._v_lock = threading.Lock()
        self.firmware_dir = './firmware'
        
        self._next_update = -1
        self._update_timer = None
        self._update_delay = config.UPDATE_DELAY
        self._device_dict = dict()
        self._keys_dict = dict()
        
        self._clientApp = LoraServerClient()
        self._loraserver_jwt = None
        
        self._service_profile = config.LORASERVER_SERVICE_PROFILE
        self._downlink_datarate = config.LORASERVER_DOWNLINK_DR
        self._downlink_freq = config.LORASERVER_DOWNLINK_FREQ
    
        self._m_th = threading.Thread(target=self._firmware_monitor)
        self._m_th.start()
        
        self.multicast_updaters = []
        self._updater_lock = threading.Lock()
        
    def stop(self):
        self._exit = True

    def set_mqtt_client(self, client):
        self.p_client = client
        
    def _firmware_monitor(self):
        self._loraserver_jwt = self._clientApp.login()

        while not self._exit:
            with self._v_lock:
                self._latest_version = self._check_version()
                
            time.sleep(5)
        
    def process_rx_msg(self, payload):

        dev_eui = self.get_device_eui(payload)
        dev_msg = self.decode_device_msg(payload)
        if self.MSG_HEADER in dev_msg:
            msg_type = self.get_msg_type(dev_msg.decode())
            if msg_type == self.UPDATE_INFO_MSG:
                self._send_update_info(dev_eui, dev_msg.decode())
            elif msg_type == self.MULTICAST_KEY_REQ:
                self._send_multicast_keys(dev_eui)
            elif msg_type == self.LISTENING_MSG:
                self._send_listening_reply(dev_eui)
                
    def _send_listening_reply(self, dev_eui):
        
        msg = bytearray()
        msg.extend(self.MSG_HEADER)
        msg.extend(b',' + str(self.LISTENING_REPLY).encode())
        msg.extend(b',' + self.MSG_TAIL)
        
        self.send_payload(dev_eui, msg)
                
    def _send_multicast_keys(self, dev_eui):
        
        msg = bytearray()
        msg.extend(self.MSG_HEADER)
        msg.extend(b',' + str(self.MULTICAST_KEY_REPLY).encode())
        
        if dev_eui in self._device_dict:
            multicast_param_key = self._device_dict[dev_eui]
            multicast_param = self._keys_dict[multicast_param_key]
            
            msg.extend(b',' + multicast_param[1])
            msg.extend(b',' + multicast_param[2])
            msg.extend(b',' + multicast_param[3])
        else:
            msg.extend(b',,,')
            
        msg.extend(b',' + self.MSG_TAIL)
        
        self.send_payload(dev_eui, msg)
    
    def get_device_eui(self, payload):
        dev_eui = None
        try:
            dev_eui = json.loads(payload)["devEUI"]
        except Exception as ex:
            print("Exception extracting device eui")

        return dev_eui
    
    def get_msg_type(self, msg):
        msg_type = -1

        try:
            msg_type = int(msg.split(",")[1])
        except Exception as ex:
            print("Exception getting message type")

        return msg_type
    
    def decode_device_msg(self, payload):
        dev_msg = None
        try:
            rx_pkt = json.loads(payload)
            dev_msg = base64.b64decode(rx_pkt["data"])
        except Exception as ex:
            print("Exception decoding device message")
        return dev_msg
    
    def _create_multicast_group(self, update_info):
        service_id = self._clientApp.request_service_profile_id(self._service_profile, self._loraserver_jwt)
        
        group_name = update_info.replace(',','-')
        multicast_param = self._clientApp.create_multicast_group(self._downlink_datarate, self._downlink_freq, group_name, service_id, self._loraserver_jwt)
    
        return multicast_param
        
    def _init_update_params(self, dev_eui, dev_version, latest_version):
        if self._next_update <= 0:
            self._next_update = int(time.time()) + self._update_delay
            self._update_timer = threading.Timer(self._update_delay, self.update_proc)
            self._update_timer.start()
        
        update_info = dev_version.strip() + ',' + latest_version.strip()
        self._device_dict[dev_eui] = update_info
        if update_info not in self._keys_dict:
            multicast_param = self._create_multicast_group(update_info)
            self._keys_dict[update_info] = multicast_param
            self._clientApp.add_device_multicast_group(dev_eui, multicast_param[0], self._loraserver_jwt)
        
    def _send_update_info(self, dev_eui, msg):
        print(msg)
        dev_version = self.get_device_version(msg)
        print("Device eui: {}, Device Version: {}".format(dev_eui, dev_version))

        if len(dev_version) > 0:
            version = self.get_latest_version()
            if LooseVersion(version) > LooseVersion(dev_version):
                self._init_update_params(dev_eui, dev_version, version)
            msg = self._create_update_info_msg(version, dev_version)
            self.send_payload(dev_eui, msg)
            
    def get_device_version(self, msg):
        dev_version = None
        try:
            dev_version = msg.split(",")[2]
        except Exception as ex:
            print("Exception extracting device version")

        return dev_version
    
    def _check_version(self):
        latest = '0.0.0'
        for d in os.listdir(self.firmware_dir):
            if os.path.isfile(d):
                continue
            if latest is None or LooseVersion(latest) < LooseVersion(d):
                latest = d
                
        return latest
    
    def get_latest_version(self):
        with self._v_lock:
            return self._latest_version
        
    def is_empty_multicast_queue(self, jwt, multicast_group_id):
        queue_length =self._clientApp.multicast_queue_length(jwt, multicast_group_id)
        if queue_length > 0:
            return False
        else:
            return True
        
    def clear_multicast_group(self, dict_key):
        with self._updater_lock:
            if dict_key in self._keys_dict:
                group_id = self._keys_dict[dict_key][0]
                self._clientApp.delete_multicast_group(group_id)
                del self._keys_dict[dict_key]
            
            self._device_dict = {key:val for key, val in self._device_dict.items() if val != dict_key}
        
            for updater in self.multicast_updaters:
                if updater.tag == dict_key:
                    self.multicast_updaters.remove(updater)
                
            if len(self.multicast_updaters) == 0:
                self._next_update = -1
                self._update_timer = None
        
    def update_proc(self):
        
        for dict_key in self._keys_dict:
            dev_version = dict_key.split(',')[0]
            latest_version = dict_key.split(',')[1]
            multicast_group_id = self._keys_dict[dict_key][0]
            upater = updateHandler(dev_version, latest_version, self._clientApp, self._loraserver_jwt, multicast_group_id, self)
            
            self.multicast_updaters.append(upater)
            
    def _get_update_type(self, need_updating, device_version):
        update_type = b',' + self.NO_UPDATE
        print(os.path.isdir(self.firmware_dir + '/' + device_version))
        if need_updating:
            if os.path.isdir(self.firmware_dir + '/' + device_version):
                return b',' + self.DIFF_UPDATE
            else:
                return b',' + self.FULL_UPDATE
        
        return update_type
    
    def _create_update_info_msg(self, version, device_version):
        msg = bytearray()
        msg.extend(self.MSG_HEADER)
        msg.extend(b',' + str(self.UPDATE_INFO_REPLY).encode())
        msg.extend(b',' + version.encode())
        need_updating = self._next_update > 0
        update_type = self._get_update_type(need_updating, device_version)
        msg.extend(update_type)
        if need_updating:
            msg.extend(b',' + str(int(self._next_update)).encode())
        else:
            msg.extend(b',-1')
        msg.extend(b',' + str(int(time.time())).encode())
        msg.extend(b',' + self.MSG_TAIL)
        return msg
    
    def send_payload(self, dev_eui, data):
        b64Data = base64.b64encode(data)
        payload = '{"reference": "abcd1234" ,"fPort":1,"data": "' + b64Data.decode() + '"}'
        self.p_client.publish(topic="application/" + str(config.LORASERVER_APP_ID) + "/device/" + dev_eui + "/tx",payload=payload)
