from network import LoRa
import socket
import binascii
import struct

# Initialize LoRa in LORAWAN mode.
# Please pick the region that matches where you are using the device:
# Asia = LoRa.AS923
# Australia = LoRa.AU915
# Europe = LoRa.EU868
# United States = LoRa.US915
lora = LoRa(mode=LoRa.LORAWAN, region=LoRa.EU868)

# create an ABP authentication params
dev_addr = struct.unpack(">l", binascii.unhexlify('00000005'))[0]
nwk_swkey = binascii.unhexlify('2B7E151628AED2A6ABF7158809CF4F3C')
app_swkey = binascii.unhexlify('2B7E151628AED2A6ABF7158809CF4F3C')

# join a network using ABP (Activation By Personalization)
lora.join(activation=LoRa.ABP, auth=(dev_addr, nwk_swkey, app_swkey))

# create a LoRa socket
s = socket.socket(socket.AF_LORA, socket.SOCK_RAW)

# set the LoRaWAN data rate
s.setsockopt(socket.SOL_LORA, socket.SO_DR, 5)

# make the socket non-blocking
s.setblocking(False)

# send some data
s.send(bytes([0x01, 0x02, 0x03]))

# get any data received...
data = s.recv(64)
print(data)
