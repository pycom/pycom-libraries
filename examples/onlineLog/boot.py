from machine import UART
import machine
import os
from network import WLAN

uart = UART(0, baudrate=115200)
os.dupterm(uart)

wifi_ssid = 'YOURWIFISSID'
wifi_pass = 'YOURWIFIPASSWORD'

if machine.reset_cause() != machine.SOFT_RESET:
        
    wlan = WLAN(mode=WLAN.STA)
    
    wlan.connect(wifi_ssid, auth=(WLAN.WPA2, wifi_pass), timeout=5000)

    while not wlan.isconnected(): 
         machine.idle()


machine.main('main.py')
