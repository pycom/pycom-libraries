#!/usr/bin/env python
#
# Copyright (c) 2019, Pycom Limited.
#
# This software is licensed under the GNU GPL version 3 or any
# later version, with permitted additional terms. For more information
# see the Pycom Licence v1.0 document supplied with this file, or
# available at https://www.pycom.io/opensource/licensing
#

import urllib.request
import binascii
import base64
import os
import json
import config

login_payload = {
  "password": "string",
  "username": "string"
}
    
mcGroup_payload = {
    "multicastGroup": {
        "dr": 0,
        "fCnt": 0,
        "frequency": 0,
        "groupType": "CLASS_C",
        "id": "string",
        "mcAddr": "string",
        "mcAppSKey": "string",
        "mcNwkSKey": "string",
        "name": "string",
        "pingSlotPeriod": 0,
        "serviceProfileID": "string"
    }
}
    
mcQueue_payload = {
    "multicastQueueItem": {
        "data": "string",
        "fCnt": 0,
        "fPort": 1,
        "multicastGroupID": "string"
  }
}
    
mcAddDevice_payload = {
    "devEUI": "string",
    "multicastGroupID": "string"
}
  
class LoraServerClient:
    
    def __init__(self):
        self.server = config.LORASERVER_URL
        self.port = config.LORASERVER_API_PORT
        self.username = config.LORASERVER_USER
        self.passwd = config.LORASERVER_PASS
        
    def login(self):
        url = self.server + ':' + str(self.port) + '/api/internal/login'
        
        login_payload["password"] = self.passwd
        login_payload["username"] = self.username
        
        payload = bytes(json.dumps(login_payload),'utf-8')
        
        try:
            r = urllib.request.Request(url, data= payload, method= 'POST')
            r.add_header("Content-Type", "application/json")
            r.add_header("Accept", "application/json")
            
            with urllib.request.urlopen(r) as f:
                return json.loads(f.read().decode('utf-8'))['jwt']
            
        except Exception as ex:
            print("Error getting the jwt: {}".format(ex))
            
        return None
    
    def parse_service_profile_list(self, response, profile_name):
        
        try:
            json_obj = json.loads(response)
            for sp_obj in json_obj["result"]:
                if sp_obj["name"] == profile_name:
                    return sp_obj["id"]
        except Exception as ex:
            print("Error parsing service profile list: {}".format(ex))
            
        return None
        
    def request_service_profile_id(self, profile_name, jwt):
        url = self.server + ':' + str(self.port) + '/api/service-profiles?limit=100'
        
        try:
            r = urllib.request.Request(url, method= 'GET')
            r.add_header("Accept", "application/json")
            r.add_header("Grpc-Metadata-Authorization", "Bearer " + jwt)
            
            with urllib.request.urlopen(r) as f:
                return self.parse_service_profile_list(f.read().decode('utf-8'), profile_name)
            
        except Exception as ex:
            print("Error getting service profile id: {}".format(ex))
            
        return None
    
    def create_multicast_group(self, dr, freq, group_name, serviceProfileID, jwt):
        
        group_id = self.generate_random_id()
        mcAddr = self.generate_randon_addr()
        mcAppSKey = self.generate_random_key()
        mcNwkSKey = self.generate_random_key()
        
        url = self.server + ':' + str(self.port) + '/api/multicast-groups'
        
        mcGroup_payload["multicastGroup"]["dr"] = dr
        mcGroup_payload["multicastGroup"]["frequency"] = freq
        mcGroup_payload["multicastGroup"]["id"] = group_id.decode("utf-8")
        mcGroup_payload["multicastGroup"]["mcAddr"] = mcAddr.decode("utf-8") 
        mcGroup_payload["multicastGroup"]["mcAppSKey"] = mcAppSKey.decode("utf-8") 
        mcGroup_payload["multicastGroup"]["mcNwkSKey"] = mcNwkSKey.decode("utf-8") 
        mcGroup_payload["multicastGroup"]["name"] = group_name
        mcGroup_payload["multicastGroup"]["serviceProfileID"] = serviceProfileID
        
        payload = bytes(json.dumps(mcGroup_payload),'utf-8')
        
        
        try:
            r = urllib.request.Request(url, data= payload, method= 'POST')
            r.add_header("Content-Type", "application/json")
            r.add_header("Accept", "application/json")
            r.add_header("Grpc-Metadata-Authorization", "Bearer " + jwt)
            
            with urllib.request.urlopen(r) as f:
                resp = f.read().decode('utf-8')
                if '"id":' in resp:
                    multicast_id = json.loads(resp)["id"]
                    return (multicast_id, mcAddr, mcNwkSKey, mcAppSKey)
                else:
                    return None
        except Exception as ex:
            print("Error creating multicast data: {}".format(ex))
            
        return None
    
    def delete_multicast_group(self, group_id):
        
        url = self.server + ':' + str(self.port) + '/api/multicast-groups/' + group_id
        
        try:
            r = urllib.request.Request(url, method = 'DELETE')
            
            with urllib.request.urlopen(r) as f:
                return f.getcode() == 200
            
        except Exception as ex:
            print("Error deleting multicast group: {}".format(ex))
        
        return False
    
    def add_device_multicast_group(self, devEUI, group_id, jwt):
        
        url = self.server + ':' + str(self.port) + '/api/multicast-groups/' + group_id + '/devices'
        
        mcAddDevice_payload["devEUI"] = devEUI
        mcAddDevice_payload["multicastGroupID"] = group_id
        
        payload = json.dumps(mcAddDevice_payload).encode('utf-8')
        
        try:
            r = urllib.request.Request(url, data= payload, method= 'POST')
            r.add_header("Content-Type", "application/json")
            r.add_header("Accept", "application/json")
            r.add_header("Grpc-Metadata-Authorization", "Bearer " + jwt)
            
            with urllib.request.urlopen(r) as f:
                return f.getcode() == 200
            
        except Exception as ex:
            print("Error adding device to multicast group: {}".format(ex))
            
        return False
    
    def request_multicast_keys(self, group_id, jwt):
        
        url = self.server + ':' + str(self.port) + '/api/multicast-groups/' + group_id
        
        try:
            r = urllib.request.Request(url, method= 'GET')
            r.add_header("Accept", "application/json")
            r.add_header("Grpc-Metadata-Authorization", "Bearer " + jwt)
            
            with urllib.request.urlopen(r) as f:
                resp = f.read().decode('utf-8')
                if "mcNwkSKey" in resp:
                    json_resp = json.loads(resp)["multicastGroup"]
                    return (json_resp["mcAddr"], json_resp["mcNwkSKey"], json_resp["mcAppSKey"])
                else:
                    return None
        except Exception as ex:
            print("Error getting multicast keys: {}".format(ex))
            
        return None
        
    def generate_randon_addr(self):
        return binascii.hexlify(os.urandom(4))
    
    def generate_random_key(self):
        return binascii.hexlify(os.urandom(16))
    
    def generate_random_id(self):
        return binascii.hexlify(os.urandom(4)) + b'-' + binascii.hexlify(os.urandom(2)) + b'-' + binascii.hexlify(os.urandom(2)) \
            + b'-' + binascii.hexlify(os.urandom(2)) + b'-' + binascii.hexlify(os.urandom(6))
        
    def multicast_queue_length(self, jwt, multicast_group):
        url = self.server + ':' + str(self.port) + '/api/multicast-groups/' + multicast_group + '/queue'
        
        try:
            r = urllib.request.Request(url, method= 'GET')
            r.add_header("Content-Type", "application/json")
            r.add_header("Grpc-Metadata-Authorization", "Bearer " + jwt)
            
            with urllib.request.urlopen(r) as f:
                resp = f.read().decode('utf-8')
                if "multicastQueueItems" in resp:
                    print(resp)
                    json_resp = json.loads(resp)["multicastQueueItems"]
                    print("Len: {}".format(len(json_resp)))
                    return len(json_resp)
                else:
                    return -1
                
        except Exception as ex:
            print("Error getting multicast queue length: {}".format(ex))
            
        return -1
        
    
    def send(self, jwt, multicast_group, data):
        url = self.server + ':' + str(self.port) + '/api/multicast-groups/' + multicast_group + '/queue'
        
        mcQueue_payload["multicastQueueItem"]["data"] = base64.b64encode(data).decode("utf-8")
        mcQueue_payload["multicastQueueItem"]["multicastGroupID"] = multicast_group
        
        payload = bytes(json.dumps(mcQueue_payload),'utf-8')
        
        try:
            r = urllib.request.Request(url, data= payload, method= 'POST')
            r.add_header("Content-Type", "application/json")
            r.add_header("Accept", "application/json")
            r.add_header("Grpc-Metadata-Authorization", "Bearer " + jwt)
            
            with urllib.request.urlopen(r) as f:
                return f.getcode() == 200
            
        except Exception as ex:
            print("Error sending multicast data: {}".format(ex))
                  
        return False

    
    
        
