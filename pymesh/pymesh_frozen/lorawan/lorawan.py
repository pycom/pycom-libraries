""" OTAA Node example compatible with the LoPy Nano Gateway """

from network import LoRa
from network import WLAN
import socket
import binascii
import struct
import time
from machine import RTC

class Lorawan:

    def __init__(self):
        # create an OTA authentication params
        self.dev_eui = binascii.unhexlify('007926C9EAE4C922')
        self.app_eui = binascii.unhexlify('70B3D57ED001D8C8')
        self.app_key = binascii.unhexlify('2C4D6AE9CEBA8B0EB4430C33C17750CB')

    def send(self):
        t0 = time.time()
        print("LoRaWAN start")
        lora = LoRa(mode=LoRa.LORAWAN, region=LoRa.EU868)

        # set the 3 default channels to the same frequency (must be before sending the OTAA join request)
        lora.add_channel(0, frequency=config.LORA_FREQUENCY, dr_min=0, dr_max=5)
        lora.add_channel(1, frequency=config.LORA_FREQUENCY, dr_min=0, dr_max=5)
        lora.add_channel(2, frequency=config.LORA_FREQUENCY, dr_min=0, dr_max=5)

        # join a network using OTAA
        lora.join(activation=LoRa.OTAA, auth=(self.dev_eui, self.app_eui, self.app_key), timeout=0, dr=config.LORA_NODE_DR)

        # wait until the module has joined the network
        while not lora.has_joined():
            time.sleep(2.5)
            print('Not joined yet...', time.localtime())

        # remove all the non-default channels
        for i in range(3, 16):
            lora.remove_channel(i)

        # create a LoRa socket
        s = socket.socket(socket.AF_LORA, socket.SOCK_RAW)

        # set the LoRaWAN data rate
        s.setsockopt(socket.SOL_LORA, socket.SO_DR, config.LORA_NODE_DR)

        # make the socket non-blocking
        s.setblocking(False)

        pkt = b'PKT #' + bytes([i])
        print('Sending:', pkt)
        s.send(pkt)
        print("LoRaWAN done in ", time.time() - t0, " seconds")

class config:
    # for EU868
    LORA_FREQUENCY = 867500000
    LORA_GW_DR = "SF7BW125" # DR_5
    LORA_NODE_DR = 5
