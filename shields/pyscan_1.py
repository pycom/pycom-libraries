'''
Simple Pyscan NFC / MiFare Classic Example
Copyright (c) 2019, Pycom Limited.

This example continuously sends a REQA for ISO14443A card type
If a card is discovered, it will read the UID
If DECODE_CARD = True, will attempt to authenticate with CARDkey
If authentication succeeds will attempt to read sectors from the card
'''

from pycoproc_1 import Pycoproc
from MFRC630 import MFRC630
from LIS2HH12 import LIS2HH12
from LTR329ALS01 import LTR329ALS01
import time
import pycom

#add your card UID here
VALID_CARDS = [[0x43, 0x95, 0xDD, 0xF8],
               [0x43, 0x95, 0xDD, 0xF9],
               [0x46, 0x5A, 0xEB, 0x7D, 0x8A, 0x08, 0x04]]


# This is the default key for an unencrypted MiFare card
CARDkey = [ 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF ]
DECODE_CARD = False

py = Pycoproc(Pycoproc.PYSCAN)
nfc = MFRC630(py)
lt = LTR329ALS01(py)
li = LIS2HH12(py)

pybytes_enabled = False
if 'pybytes' in globals():
    if(pybytes.isconnected()):
        print('Pybytes is connected, sending signals to Pybytes')
        pybytes_enabled = True

RGB_BRIGHTNESS = 0x8

RGB_RED = (RGB_BRIGHTNESS << 16)
RGB_GREEN = (RGB_BRIGHTNESS << 8)
RGB_BLUE = (RGB_BRIGHTNESS)

counter = 0

def check_uid(uid, len):
    return VALID_CARDS.count(uid[:len])

def send_sensor_data(name, timeout):
    if(pybytes_enabled):
        while(True):
            pybytes.send_signal(2, lt.light())
            pybytes.send_signal(3, li.acceleration())
            time.sleep(timeout)

# Make sure heartbeat is disabled before setting RGB LED
pycom.heartbeat(False)

# Initialise the MFRC630 with some settings
nfc.mfrc630_cmd_init()

print('Scanning for cards')
while True:
    # Send REQA for ISO14443A card type
    atqa = nfc.mfrc630_iso14443a_WUPA_REQA(nfc.MFRC630_ISO14443_CMD_REQA)
    if (atqa != 0):
        # A card has been detected, read UID
        print('A card has been detected, reading its UID ...')
        uid = bytearray(10)
        uid_len = nfc.mfrc630_iso14443a_select(uid)
        print('UID has length {}'.format(uid_len))
        if (uid_len > 0):
            # A valid UID has been detected, print details
            counter += 1
            print("%d\tUID [%d]: %s" % (counter, uid_len, nfc.format_block(uid, uid_len)))
            if DECODE_CARD:
                # Try to authenticate with CARD key
                nfc.mfrc630_cmd_load_key(CARDkey)
                for sector in range(0, 16):
                    if (nfc.mfrc630_MF_auth(uid, nfc.MFRC630_MF_AUTH_KEY_A, sector * 4)):
                        pycom.rgbled(RGB_GREEN)
                        # Authentication was sucessful, read card data
                        readbuf = bytearray(16)
                        for b in range(0, 4):
                            f_sect = sector * 4 + b
                            len = nfc.mfrc630_MF_read_block(f_sect, readbuf)
                            print("\t\tSector %s: Block: %s: %s" % (nfc.format_block([sector], 1), nfc.format_block([b], 1), nfc.format_block(readbuf, len)))
                    else:
                        print("Authentication denied for sector %s!" % nfc.format_block([sector], 1))
                        pycom.rgbled(RGB_RED)
                # It is necessary to call mfrc630_MF_deauth after authentication
                # Although this is also handled by the reset / init cycle
                nfc.mfrc630_MF_deauth()
            else:
                #check if card uid is listed in VALID_CARDS
                if (check_uid(list(uid), uid_len)) > 0:
                    print('Card is listed, turn LED green')
                    pycom.rgbled(RGB_GREEN)
                    if(pybytes_enabled):
                        pybytes.send_signal(1, ('Card is listed', uid))
                else:
                    print('Card is not listed, turn LED red')
                    pycom.rgbled(RGB_RED)
                    if(pybytes_enabled):
                        pybytes.send_signal(1, ('Unauthorized card detected', uid))

    else:
        pycom.rgbled(RGB_BLUE)
    # We could go into power saving mode here... to be investigated
    nfc.mfrc630_cmd_reset()
    time.sleep(.5)
    # Re-Initialise the MFRC630 with settings as these got wiped during reset
    nfc.mfrc630_cmd_init()
