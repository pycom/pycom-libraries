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
    OTAA Node example  as per LoRaWAN AU915 regional specification
    - tested works with a LoRaServer, shall works on TTN servers
    - This example uses 8 channels so you will need an 8 channel GW
        (not a 1 channel GW like the NanoGateway)
"""

from network import LoRa
import socket
import binascii
import struct
import time

LORA_FREQUENCY = 915200000 # start of the 1st subband
LORA_NODE_DR = 4
'''
    utility function to setup the lora channels
'''
def prepare_channels(lora, channel, data_rate):

    AU915_FREQUENCIES = [
        { "chan": 64, "fq": "915200000" }
    ]
    if not channel in range(64,65):
        raise RuntimeError("only channel 64 is implemented in this example)")
    upstream = (item for item in AU915_FREQUENCIES if item["chan"] == channel).__next__()

    lora.add_channel(int(upstream.get('chan')), frequency=int(upstream.get('fq')), dr_min=0, dr_max=int(data_rate))
    print("*** Adding channel up %s %s" % (upstream.get('chan'), upstream.get('fq')))

    for index in range(0, 71):
        if index != upstream.get('chan'):
            lora.remove_channel(index)

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
    Main operations: this is sample code for LoRaWAN on AU915
'''

lora = LoRa(mode=LoRa.LORAWAN, region=LoRa.AU915, device_class=LoRa.CLASS_C)

# create an OTA authentication params
dev_eui = binascii.unhexlify('0000000000000000')
app_key = binascii.unhexlify('a926e5bb85271f2d') # not used leave empty loraserver.io
nwk_key = binascii.unhexlify('a926e5bb85271f2da0440f2f4200afe3')

prepare_channels(lora, 64, 5)

# join a network using OTAA
lora.join(activation=LoRa.OTAA, auth=(dev_eui, app_key, nwk_key), timeout=0,  dr=0) # DR is 2 in v1.1rb but 0 worked for ne

# wait until the module has joined the network
print('Over the air network activation ... ', end='')
while not lora.has_joined():
    time.sleep(2.5)
    print('.', end='')
print('')

for i in range(0, 8):
    fq = LORA_FREQUENCY + (i * 200000)
    lora.add_channel(i, frequency=fq, dr_min=0, dr_max=LORA_NODE_DR)
    print("AU915 Adding channel up %s %s" % (i, fq))


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
