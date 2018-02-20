from network import LoRa
import socket

# Initialize LoRa in LORA mode.

# More params can be given, like frequency, tx power and spreading factor.
# Please pick the region that matches where you are using the device:
# Asia = LoRa.AS923
# Australia = LoRa.AU915
# Europe = LoRa.EU868
# United States = LoRa.US915
lora = LoRa(mode=LoRa.LORA, region=LoRa.EU868)

# create a raw LoRa socket
s = socket.socket(socket.AF_LORA, socket.SOCK_RAW)
s.setblocking(False)

# send some data
s.send(bytes([0x01, 0x02, 0x03])

# get any data received...
data = s.recv(64)
print(data)
