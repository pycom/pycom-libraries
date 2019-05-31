#!/usr/bin/env python
#
# Copyright (c) 2019, Pycom Limited.
#
# This software is licensed under the GNU GPL version 3 or any
# later version, with permitted additional terms. For more information
# see the Pycom Licence v1.0 document supplied with this file, or
# available at https://www.pycom.io/opensource/licensing
#

from loranet import LoraNet
from ota import LoraOTA
from network import LoRa
import machine
import utime

def main():
    LORA_FREQUENCY = 868100000
    LORA_NODE_DR = 5
    LORA_REGION = LoRa.EU868
    LORA_DEVICE_CLASS = LoRa.CLASS_C
    LORA_ACTIVATION = LoRa.OTAA
    LORA_CRED = ('240ac4fffe0bf998', '948c87eff87f04508f64661220f71e3f', '5e6795a5c9abba017d05a2ffef6ba858')

    lora = LoraNet(LORA_FREQUENCY, LORA_NODE_DR, LORA_REGION, LORA_DEVICE_CLASS, LORA_ACTIVATION, LORA_CRED)
    lora.connect()

    ota = LoraOTA(lora)

    while True:
        rx = lora.receive(256)
        if rx:
            print('Received user message: {}'.format(rx))

        utime.sleep(2)

main()

#try:
#    main()
#except Exception as e:
#    print('Firmware exception: Reverting to old firmware')
#    LoraOTA.revert()
