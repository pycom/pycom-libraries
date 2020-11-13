# Copyright (c) 2020, Pycom Limited.
#
# This software is licensed under the GNU GPL version 3 or any
# later version, with permitted additional terms. For more information
# see the Pycom Licence v1.0 document supplied with this file, or
# available at https://www.pycom.io/opensource/licensing

from network import Bluetooth
import time
import msgpack
import machine
import ubinascii

VERSION = "1.0.0"

class BleServices:

    def __init__(self, ble_name):
        # self.mesh_mac = mesh_mac
        self.ble_name = ble_name
        self.on_disconnect = None
        self._init()

    def _init(self):
        self.status = {
            'connected' : False
        }

        bluetooth = Bluetooth(modem_sleep=False)
        adv_name = self.ble_name
        bluetooth.set_advertisement(name=adv_name, service_uuid=0xec00)
        print("BLE name:", adv_name)

        bluetooth.callback(trigger=Bluetooth.CLIENT_CONNECTED | Bluetooth.CLIENT_DISCONNECTED, handler=self.conn_cb)
        bluetooth.advertise(True)

        srv_rx = bluetooth.service(uuid=0xec00, isprimary=True)
        self.chr_rx = srv_rx.characteristic(uuid=0xec0e, value=0)

        srv_tx = bluetooth.service(uuid=0xed00, isprimary=True)
        self.chr_tx = srv_tx.characteristic(uuid=0xed0e, value=0)

        self.unpacker = None

        srv_mac = bluetooth.service(uuid=0xee00, isprimary=True)
        self.chr_mac = srv_mac.characteristic(uuid=0xee0e, permissions=(1 << 0), properties=(1 << 1) | (1 << 4), value='mac')
        self.chr_mac.callback(trigger=Bluetooth.CHAR_READ_EVENT, handler=self.chr_mac_handler)

        srv_key = bluetooth.service(uuid=0xea00, isprimary=True, nbr_chars=2)
        self.chr_get_key = srv_key.characteristic(uuid=0xea0e, permissions=(1 << 0), properties=(1 << 1) | (1 << 4), value='key')
        self.chr_set_key = srv_key.characteristic(uuid=0xea0f, value='key')
        self.chr_set_key.callback(trigger=Bluetooth.CHAR_WRITE_EVENT, handler=self.chr_set_key_handler)
        self.chr_get_key.callback(trigger=Bluetooth.CHAR_READ_EVENT, handler=self.chr_get_key_handler)

        self.mesh = None

    def chr_get_key_handler(self, chr, data):
        events = chr.events()
        if events & Bluetooth.CHAR_READ_EVENT:
            key = self.get_mesh_key()
            print(key)
            chunks=[key[i:i+20] for i in range(0, len(key), 20)]
            for chunk in chunks:
                print(chunk)
                chr.value(chunk)

    def chr_set_key_handler(self, chr, data):
        events = chr.events()
        if events & Bluetooth.CHAR_WRITE_EVENT:
            val = chr.value()
            print("written val:", val)
            # self.set_mesh_key(val)

    def chr_mac_handler(self, chr, data):
        events = chr.events()
        if events & Bluetooth.CHAR_READ_EVENT:
            ble_mac_str = ubinascii.hexlify(machine.unique_id()).decode("utf-8")
            ble_mac_int = int(ble_mac_str,16) + 2
            ble_mac_str = str(hex(ble_mac_int))
            b=ble_mac_str[2:]
            ble_mac_str=b[:2]+":"+b[2:4]+":"+b[4:6]+":"+b[6:8]+":"+b[8:10]+":"+b[10:]
            chr.value(ble_mac_str.upper())

    def conn_cb(self, bt_o):
        #global ble_connected
        events = bt_o.events()
        if  events & Bluetooth.CLIENT_CONNECTED:
            self.status['connected'] = True
            print("Client connected")
        elif events & Bluetooth.CLIENT_DISCONNECTED:
            self.status['connected'] = False

            if self.on_disconnect:
                self.on_disconnect()

            print("Client disconnected")
        pass

    def unpacker_set(self, unpacker):
        self.unpacker = unpacker

    def close(self):
        bluetooth = Bluetooth()
        bluetooth.disconnect_client()
        bluetooth.deinit()
        pass

    def restart(self):
        print("BLE disconnnect client")
        bluetooth = Bluetooth()
        bluetooth.disconnect_client()
        time.sleep(2)
        self.status['connected'] = False
        if self.on_disconnect:
            self.on_disconnect()

        # bluetooth.deinit()
        # time.sleep(1)
        # self._init()
        pass

    def set_mesh_key(self, key):
        rslt = self.mesh.set_mesh_key(key)
        return rslt

    def get_mesh_key(self):
        key = self.mesh.get_mesh_key()
        return key
