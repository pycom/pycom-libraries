import socket
import time
import pycom
import struct
from network import LoRa
from machine import I2C
import bh1750fvi

LORA_PKG_FORMAT = "!BH"
LORA_CONFIRM_FORMAT = "!BB"

DEVICE_ID = 1

pycom.heartbeat(False)

lora = LoRa(mode=LoRa.LORA, tx_iq=True, frequency = 863000000)
lora_sock = socket.socket(socket.AF_LORA, socket.SOCK_RAW)
lora_sock.setblocking(False)

i2c = I2C(0, I2C.MASTER, baudrate=100000)
light_sensor = bh1750fvi.BH1750FVI(i2c, addr=i2c.scan()[0])

while(True):
    msg = struct.pack(LORA_PKG_FORMAT, DEVICE_ID, light_sensor.read())
    lora_sock.send(msg)

    pycom.rgbled(0x150000)

    wait = 5
    while (wait > 0):
        wait = wait - 0.1
        time.sleep(0.1)
        recv_data = lora_sock.recv(64)
        
        if (len (recv_data) >= 2):
            status, device_id = struct.unpack(LORA_CONFIRM_FORMAT, recv_data)
            
            if (device_id == DEVICE_ID and status == 200):
                pycom.rgbled(0x001500)
                wait = 0

    time.sleep(1)