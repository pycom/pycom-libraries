'''
Simple Pyscan NFC / MiFare Classic Example
Copyright (c) 2018, Pycom Limited.

This example continuously sends a REQA for ISO14443A card type
If a card is discovered, it will read the UID
If DECODE_CARD = True, will attempt to authenticate with CARDkey
If authentication succeeds will attempt to read sectors from the card
'''

from pyscan import Pyscan
from MFRC630 import MFRC630
import time
import pycom

# This is the default key for an unencrypted MiFare card
CARDkey = [ 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF ]
DECODE_CARD = False

py = Pyscan()
nfc = MFRC630(py)

RGB_BRIGHTNESS = 0x8

RGB_RED = (RGB_BRIGHTNESS << 16)
RGB_GREEN = (RGB_BRIGHTNESS << 8)
RGB_BLUE = (RGB_BRIGHTNESS)

counter = 0

# Make sure heartbeat is disabled before setting RGB LED
pycom.heartbeat(False)

# Initialise the MFRC630 with some settings
nfc.mfrc630_cmd_init()

while True:
    # Send REQA for ISO14443A card type
    atqa = nfc.mfrc630_iso14443a_WUPA_REQA(nfc.MFRC630_ISO14443_CMD_REQA)
    if (atqa != 0):
        # A card has been detected, read UID
        uid = bytearray(10)
        uid_len = nfc.mfrc630_iso14443a_select(uid)
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
                # If we're not trying to authenticate, show green when a UID > 0 has been detected
                pycom.rgbled(RGB_GREEN)
    else:
        pycom.rgbled(RGB_BLUE)
    # We could go into power saving mode here... to be investigated
    nfc.mfrc630_cmd_reset()
    time.sleep(.5)
    # Re-Initialise the MFRC630 with settings as these got wiped during reset
    nfc.mfrc630_cmd_init()
