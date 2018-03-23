#!/usr/bin/env python
import struct
import crc
import stp
import time
import os
from machine import UART
from machine import SD


FFF_FMT = "<4sIIIIIIIHHIHHIHHHH"
FFF_SLIM_FMT = "<4sIIIIIIIHHHH"
FFF_FEATURES_SLIM = 1 << 0
FFF_MAGIC = "FFF!"

SFFF_MAGIC = "SFFF"             # Firmware
SUFF_MAGIC = "SUFF"             # Updater
TEST_MAGIC = "TEST"             # Test
DIFF_MAGIC = "DIFF"             # Diff Upgrade
UPGR_MAGIC = "UPGR"             # Generic raw upgrade
RASR_MAGIC = "RASR"             # Generic raw rasterize


def read_rsp(s, size=None, timeout=-1):
    if timeout < 0:
        timeout = 20000
    elif timeout is None:
        timeout = 0
    while not s.any() and timeout > 0:
        time.sleep_ms(1)
        timeout -= 1

    if size is not None:
        rsp = s.read(size)
    else:
        rsp = s.read()
    if rsp is not None:
        return rsp
    else:
        return b''

def print_pretty_response(rsp):
    lines = rsp.decode('ascii').split('\r\n')
    for line in lines:
        if line:
            print(line)


def wait_for_modem(s, send=True, expected=b'OK'):
    while True:
        if send:
            s.write("AT\r\n")
        rsp = read_rsp(s, timeout=50)
        if expected in rsp:
            print()
            break
        else:
            print('.', end='', flush=True)
            time.sleep(0.5)

def run(file_path, baudrate):
    abort = False

    print('<<< Welcome to the SQN3330 firmware updater >>>')

    if '/sd' in file_path:
        sd = SD()
        time.sleep(0.5)
        os.mount(sd, '/sd')
        time.sleep(0.5)

    blobsize = os.stat(file_path)[6]
    blob = open(file_path, "rb")

    if 'FiPy' in os.uname().sysname:
        pins = ('P20', 'P18', 'P19', 'P17')
    else:
        pins = ('P5', 'P98', 'P7', 'P99')

    s = UART(1, baudrate=baudrate, pins=pins, timeout_chars=100)
    s.read()

    # disable echo
    s.write("ATE0\r\n")
    response = read_rsp(s)

    print('Entering recovery mode')
    s.write("AT+SMSWBOOT=3,0\r\n")
    response = read_rsp(s)
    if b'OK' in response:
        print('Resetting.', end='', flush=True)
        s.write('AT^RESET\r\n')
        wait_for_modem(s, send=False, expected=b'+SHUTDOWN')
        time.sleep(2)
        wait_for_modem(s)
        s.write("AT\r\n")
        s.write("AT\r\n")
    else:
        raise OSError('AT+SMSWBOOT=3,0 failed!')

    time.sleep(1)
    s.read()

    print('Starting STP (DO NOT DISCONNECT POWER!!!)')
    s.write('AT+SMSTPU=\"ON_THE_FLY\"\r\n')
    response = read_rsp(s, size=4)
    if response != b'OK\r\n' and response != b'\r\nOK' and response != b'\nOK':
        raise OSError("Invalid answer '%s' from the device" % response)
        blob.close()
    s.read()
    try:
        stp.start(blob, blobsize, s, baudrate, AT=False)
        print('Code download done, returning to user mode')
    except:
        blob.close()
        print('Code download failed, aborting!')
        abort = True

    time.sleep(1.5)
    s.read()
    s.write("AT+SMSWBOOT=1,0\r\n")
    response = read_rsp(s)

    print('Resetting (DO NOT DISCONNECT POWER!!!).', end='', flush=True)
    time.sleep(1.5)
    s.write("AT^RESET\r\n")
    wait_for_modem(s, send=False, expected=b'+SHUTDOWN')
    time.sleep(2)
    wait_for_modem(s, send=False, expected=b'+SYSSTART')

    if not abort:
        time.sleep(0.5)
        print('Deploying the upgrade (DO NOT DISCONNECT POWER!!!)...')
        s.write("AT+SMUPGRADE\r\n")
        response = read_rsp(s, timeout=120000)

        print('Resetting (DO NOT DISCONNECT POWER!!!).', end='', flush=True)
        time.sleep(1.5)
        s.write("AT^RESET\r\n")
        wait_for_modem(s, send=False, expected=b'+SHUTDOWN')
        time.sleep(2)
        wait_for_modem(s, send=False, expected=b'+SYSSTART')
        s.write("AT\r\n")
        s.write("AT\r\n")
        time.sleep(0.5)
        s.read()
        print('Upgrade completed!')
        print("Here's the current firmware version:")
        time.sleep(0.5)
        s.read()
        s.write("ATI1\r\n")
        response = read_rsp(s)
        print_pretty_response(response)
