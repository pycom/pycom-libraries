# main.py -- put your code here!
'''
Simple Pyscan NFC / MiFare Classic Example
Copyright (c) 2018, Pycom Limited.
This example runs the NFC discovery loop in a thread.
If a card is detected it will read the UID and compare it to VALID_CARDS
RGB LED is BLUE while waiting for card,
GREEN if card is valid, RED if card is invalid
'''

DEBUG = False  # change to True to see debug messages

from pyscan import Pyscan
from MFRC630 import MFRC630
from LIS2HH12 import LIS2HH12
from LTR329ALS01 import LTR329ALS01
import binascii
import time
import pycom
import _thread

VALID_CARDS = [[0x43, 0x95, 0xDD, 0xF8],
               [0x43, 0x95, 0xDD, 0xF9]]

py = Pyscan()
nfc = MFRC630(py)
lt = LTR329ALS01(py)
li = LIS2HH12(py)

RGB_BRIGHTNESS = 0x8

RGB_RED = (RGB_BRIGHTNESS << 16)
RGB_GREEN = (RGB_BRIGHTNESS << 8)
RGB_BLUE = (RGB_BRIGHTNESS)

# Make sure heartbeat is disabled before setting RGB LED
pycom.heartbeat(False)

# Initialise the MFRC630 with some settings
nfc.mfrc630_cmd_init()

def check_uid(uid, len):
    return VALID_CARDS.count(uid[:len])

def print_debug(msg):
    if DEBUG:
        print(msg)

def send_sensor_data(name, timeout):
    while(pybytes):
        pybytes.send_virtual_pin_value(True, 2, lt.light())
        pybytes.send_virtual_pin_value(True, 3, li.acceleration())
        time.sleep(timeout)

def discovery_loop(arg1, arg2):
    while(pybytes):
        # Send REQA for ISO14443A card type
        print_debug('Sending REQA for ISO14443A card type...')
        atqa = nfc.mfrc630_iso14443a_WUPA_REQA(nfc.MFRC630_ISO14443_CMD_REQA)
        print_debug('Response: {}'.format(atqa))
        if (atqa != 0):
            # A card has been detected, read UID
            print_debug('A card has been detected, read UID...')
            uid = bytearray(10)
            uid_len = nfc.mfrc630_iso14443a_select(uid)
            print_debug('UID has length: {}'.format(uid_len))
            if (uid_len > 0):
                print_debug('Checking if card with UID: [{:s}] is listed in VALID_CARDS...'.format(binascii.hexlify(uid[:uid_len],' ').upper()))
                if (check_uid(list(uid), uid_len)) > 0:
                    print_debug('Card is listed, turn LED green')
                    pycom.rgbled(RGB_GREEN)
                    pybytes.send_virtual_pin_value(True, 1, ('Card is listed, Access granted', uid))
                else:
                    print_debug('Card is not listed, turn LED red')
                    pycom.rgbled(RGB_RED)
                    pybytes.send_virtual_pin_value(True, 1, ('Card is not listed, Access denied', uid))
        else:
            # No card detected
            print_debug('Did not detect any card...')
            pycom.rgbled(RGB_BLUE)
            pybytes.send_virtual_pin_value(True, 1, ('Did not detect any card', 0))
        nfc.mfrc630_cmd_reset()
        time.sleep(5)
        nfc.mfrc630_cmd_init()


# This is the start of our main execution... start the thread
_thread.start_new_thread(discovery_loop, (nfc, 0))
_thread.start_new_thread(send_sensor_data, ('Thread 2',10))
