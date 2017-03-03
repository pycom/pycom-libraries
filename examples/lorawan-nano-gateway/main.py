""" LoPy LoRaWAN Nano Gateway example usage """

import config
from nanogateway import NanoGateway


nanogw = NanoGateway(id=config.GATEWAY_ID, frequency=config.LORA_FREQUENCY,
                     datarate=config.LORA_DR, ssid=config.WIFI_SSID,
                     password=config.WIFI_PASS, server=config.SERVER,
                     port=config.PORT, ntp=config.NTP, ntp_period=config.NTP_PERIOD_S)

nanogw.start()
