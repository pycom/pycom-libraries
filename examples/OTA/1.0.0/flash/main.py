from network import LoRa, WLAN
import socket
import time
from OTA import WiFiOTA
from time import sleep
import pycom
import binascii

from config import WIFI_SSID, WIFI_PW, SERVER_IP

# Turn on GREEN LED
pycom.heartbeat(False)
pycom.rgbled(0xff00)

# Setup OTA
ota = WiFiOTA(WIFI_SSID,
              WIFI_PW,
              SERVER_IP,  # Update server address
              8000)  # Update server port

# Turn off WiFi to save power
w = WLAN()
w.deinit()

# Initialize LoRa in LORAWAN mode.
lora = LoRa(mode=LoRa.LORAWAN, region=LoRa.EU868)

app_eui = binascii.unhexlify('ENTER_ME')
app_key = binascii.unhexlify('ENTER_ME')

# join a network using OTAA (Over the Air Activation)
lora.join(activation=LoRa.OTAA, auth=(app_eui, app_key), timeout=0)

# wait until the module has joined the network
while not lora.has_joined():
    time.sleep(2.5)
    print('Not yet joined...')

# create a LoRa socket
s = socket.socket(socket.AF_LORA, socket.SOCK_RAW)

# set the LoRaWAN data rate
s.setsockopt(socket.SOL_LORA, socket.SO_DR, 5)

# make the socket blocking
# (waits for the data to be sent and for the 2 receive windows to expire)
s.setblocking(True)

while True:
    # send some data
    s.send(bytes([0x04, 0x05, 0x06]))

    # make the socket non-blocking
    # (because if there's no data received it will block forever...)
    s.setblocking(False)

    # get any data received (if any...)
    data = s.recv(64)

    # Some sort of OTA trigger
    if data == bytes([0x01, 0x02, 0x03]):
        print("Performing OTA")
        # Perform OTA
        ota.connect()
        ota.update()

    sleep(5)
