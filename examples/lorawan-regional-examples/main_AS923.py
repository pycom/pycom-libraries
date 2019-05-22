#!/usr/bin/env python
#
# Copyright (c) 2019, Pycom Limited.
#
# This software is licensed under the GNU GPL version 3 or any
# later version, with permitted additional terms. For more information
# see the Pycom Licence v1.0 document supplied with this file, or
# available at https://www.pycom.io/opensource/licensing
#

"""
    OTAA Node example  as per LoRaWAN AS923 regional specification
    - compatible with the LoPy Nano Gateway and all other LoraWAN gateways
    - tested works with a LoRaServer, shall works on TTN servers
"""

from network import LoRa
import socket
import binascii
import struct
import time

LORA_CHANNEL = 1
LORA_NODE_DR = 4

'''
    utility function to setup the lora channels
'''
def prepare_channels(lora, channel, data_rate):

    AS923_FREQUENCIES = [
        { "chan": 1, "fq": "923200000" },
        { "chan": 2, "fq": "923400000" },
        { "chan": 3, "fq": "922200000" },
        { "chan": 4, "fq": "922400000" },
        { "chan": 5, "fq": "922600000" },
        { "chan": 6, "fq": "922800000" },
        { "chan": 7, "fq": "923000000" },
        { "chan": 8, "fq": "922000000" },
    ]

    if not channel in range(0, 9):
        raise RuntimeError("channels should be in 1-8 for AS923")

    if channel == 0:
        import  uos
        channel = (struct.unpack('B',uos.urandom(1))[0] % 7) + 1

    for i in range(0, 8):
        lora.remove_channel(i)

    upstream = (item for item in AS923_FREQUENCIES if item["chan"] == channel).__next__()

    # set default channels frequency
    lora.add_channel(int(upstream.get('chan')), frequency=int(upstream.get('fq')), dr_min=0, dr_max=data_rate)

    return lora

'''
    call back for handling RX packets
'''
def lora_cb(lora):
    events = lora.events()
    if events & LoRa.RX_PACKET_EVENT:
        if lora_socket is not None:
            frame, port = lora_socket.recvfrom(512) # longuest frame is +-220
            print(port, frame)
    if events & LoRa.TX_PACKET_EVENT:
        print("tx_time_on_air: {} ms @dr {}", lora.stats().tx_time_on_air, lora.stats().sftx)

'''
    Main operations: this is sample code for LoRaWAN on AS923
'''

lora = LoRa(mode=LoRa.LORAWAN, region=LoRa.AS923, device_class=LoRa.CLASS_C, adr=False, tx_power=20)

# create an OTA authentication params
dev_eui = binascii.unhexlify('0000000000000000')
app_key = binascii.unhexlify('a926e5bb85271f2d') # not used leave empty loraserver.io
nwk_key = binascii.unhexlify('a926e5bb85271f2da0440f2f4200afe3')

# join a network using OTAA
lora.join(activation=LoRa.OTAA, auth=(dev_eui, app_key, nwk_key), timeout=0, dr=2) # AS923 always joins at DR2

prepare_channels(lora, LORA_CHANNEL,  LORA_NODE_DR)

# wait until the module has joined the network
print('Over the air network activation ... ', end='')
while not lora.has_joined():
    time.sleep(2.5)
    print('.', end='')
print('')

# create a LoRa socket
lora_socket = socket.socket(socket.AF_LORA, socket.SOCK_RAW)

# set the LoRaWAN data rate
lora_socket.setsockopt(socket.SOL_LORA, socket.SO_DR, LORA_NODE_DR)

# msg are confirmed at the FMS level
lora_socket.setsockopt(socket.SOL_LORA, socket.SO_CONFIRMED, 0)

# make the socket non blocking y default
lora_socket.setblocking(False)

lora.callback(trigger=( LoRa.RX_PACKET_EVENT |
                        LoRa.TX_PACKET_EVENT |
                        LoRa.TX_FAILED_EVENT  ), handler=lora_cb)

time.sleep(4) # this timer is important and caused me some trouble ...

for i in range(0, 1000):
    pkt = struct.pack('>H', i)
    print('Sending:', pkt)
    lora_socket.send(pkt)
    time.sleep(300)
