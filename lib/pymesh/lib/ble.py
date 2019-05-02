# Copyright (c) 2019, Pycom Limited.
#
# This software is licensed under the GNU GPL version 3 or any
# later version, with permitted additional terms. For more information
# see the Pycom Licence v1.0 document supplied with this file, or
# available at https://www.pycom.io/opensource/licensing

from network import Bluetooth
import time
import msgpack

VERSION = "1.0.0"

class BleCommunication:

    def __init__(self, mesh_mac):
        self.mesh_mac = mesh_mac
        self._init()
    
    def _init(self):
        self.status = {
            'connected' : False
        }

        #bluetooth = Bluetooth(modem_sleep=False)
        bluetooth = Bluetooth()
        bluetooth.set_advertisement(name='PyGo (mac:' + str(self.mesh_mac) + ')', service_uuid=0xec00)

        bluetooth.callback(trigger=Bluetooth.CLIENT_CONNECTED | Bluetooth.CLIENT_DISCONNECTED, handler=self.conn_cb)
        bluetooth.advertise(True)

        srv_rx = bluetooth.service(uuid=0xec00, isprimary=True)
        self.chr_rx = srv_rx.characteristic(uuid=0xec0e, value=0)

        srv_tx = bluetooth.service(uuid=0xed00, isprimary=True)
        self.chr_tx = srv_tx.characteristic(uuid=0xed0e, value=0)

        self.unpacker = None

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
        
