#!/usr/bin/env python
#
# Copyright (c) 2019, Pycom Limited.
#
# This software is licensed under the GNU GPL version 3 or any
# later version, with permitted additional terms. For more information
# see the Pycom Licence v1.0 document supplied with this file, or
# available at https://www.pycom.io/opensource/licensing
#

''' A MQTT wrapper for Google Cloud IoT MQTT bridge
    Extended from umqtt.robust by Paul Sokolovsky with wrap of Google credentials

    https://github.com/micropython/micropython-lib/tree/master/umqtt.robust
    https://github.com/micropython/micropython-lib/tree/master/umqtt.simple

    Quick API Reference:
    connect(...) - Connect to a server. Returns True if this connection uses
                    persistent session stored on a server (this will be always
                    False if clean_session=True argument is used (default)).
    disconnect() - Disconnect from a server, release resources.
    ping() - Ping server (response is processed automatically by wait_msg()).
    publish() - Publish a message.
    subscribe() - Subscribe to a topic.
    set_callback() - Set callback for received subscription messages.
    wait_msg() - Wait for a server message. A subscription message will be
                  delivered to a callback set with set_callback(), any other
                  messages will be processed internally.
    check_msg() - Check if there's pending message from server. If yes, process
                   the same way as wait_msg(), if not, return immediately.
'''

import json
from binascii import b2a_base64
from binascii import a2b_base64
import ucrypto
import utime
import umqtt

def _create_unsigned_jwt(project_id, expires=60 * 60 * 24):
    header = {
        'alg': "RS256",
        'typ': 'JWT'
    }
    token = {
        'iat': utime.time(),
        'exp': utime.time() + expires,
        'aud': project_id
    }
    return b2a_base64(json.dumps(header)) + "." + \
        b2a_base64(json.dumps(token))

def _get_google_client_id(
        project_id,
        cloud_region,
        registry_id,
        device_id):
    return "projects/%s/locations/%s/registries/%s/devices/%s" % (
        project_id, cloud_region, registry_id, device_id)

def _create_google_jwt(project_id, private_key):
    to_sign = _create_unsigned_jwt(project_id)
    signed = ucrypto.generate_rsa_signature(to_sign, private_key)
    return to_sign + b'.' + b2a_base64(signed)


class GoogleMQTTClient(umqtt.MQTTClient):
    ''' Instanciate a mqtt client
    Args:
        var_int (int): An integer.
        var_str (str): A string.
        project_id (str): your google's project_id
        private_key (bytes): private key bytes in pk8s format
        cloud_region (str): your google's region
        registry_id (str): the name you had given to your registry
        device_id: (str): the human friendly device name
    '''

    DELAY = 2
    DEBUG = True
    GOOGLE_CA = '/flash/cert/google_roots.pem'
    GOOGLE_MQTT = 'mqtt.googleapis.com'

    def __init__(
            self,
            project_id,
            private_key,
            cloud_region,
            registry_id,
            device_id):
        self.private_key = private_key
        self.project_id = project_id
        self.jwt = _create_google_jwt(self.project_id, self.private_key)
        google_client_id = _get_google_client_id(
            project_id, cloud_region, registry_id, device_id)
        google_args = self._get_google_mqtt_args(self.jwt)
        super().__init__(google_client_id, self.GOOGLE_MQTT, **google_args)

    def delay(self, i):
        utime.sleep(self.DELAY + i)

    def log(self, in_reconnect, err):
        if self.DEBUG:
            if in_reconnect:
                print("mqtt reconnect: %r" % err)
            else:
                print("mqtt: %r" % err)

    def reconnect(self):
        i = 0
        while True:
            if not self.is_jwt_valid():
                self.pswd = self.jwt = _create_google_jwt(
                    self.project_id, self.private_key)
            try:
                return super().connect(False)
            except OSError as exception:
                self.log(True, exception)
                i += 1
                self.delay(i)

    def publish(self, topic, msg, retain=False, qos=0):
        if qos == 2:
            raise Exception("qos=2 not supported by mqtt bridge")

        while True:
            try:
                return super().publish(topic, msg, retain, qos)
            except OSError as exception:
                self.log(False, exception)
            self.reconnect()

    def wait_msg(self):
        while True:
            try:
                return super().wait_msg()
            except OSError as exception:
                self.log(False, exception)
            self.reconnect()

    def _get_google_mqtt_args(self, jwt):
        arguments = {
            'user': '',
            'password': jwt,
            'port': 8883,
            'ssl': True,
            'ssl_params': {
                'ca_certs': self.GOOGLE_CA
            }
        }
        return arguments

    def is_jwt_valid(self):
        try:
            token = json.loads(a2b_base64(self.jwt.decode().split('.')[1]))
        except Exception:
            return False
        return utime.time() - token.get('iat') < 60 * 60 * 24

    def set_last_will(self, topic, msg, retain=False, qos=0):
        raise Exception("set_last_will not supported by mqtt bridge")
