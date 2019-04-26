#!/usr/bin/env python
VERSION = "1.2.5"

# Copyright (c) 2019, Pycom Limited.
#
# This software is licensed under the GNU GPL version 3 or any
# later version, with permitted additional terms. For more information
# see the Pycom Licence v1.0 document supplied with this file, or
# available at https://www.pycom.io/opensource/licensing


import struct
import time
import os
import sys
import sqnscrc as crc
import sqnstp as stp

release = None

try:
    sysname = os.uname().sysname
    if 'FiPy' in sysname or 'GPy' in sysname:
        release = os.uname().release
except:
    sysname = 'Windows'

if 'FiPy' in sysname or 'GPy' in sysname:
    from machine import UART
    from machine import SD
    from network import LTE

    def reconnect_uart():
        if hasattr(LTE, 'reconnect_uart'):
            LTE.reconnect_uart()
else:   # this is a computer
    import serial
    def reconnect_uart():
        pass

class sqnsupgrade:

    global sysname

    def __init__(self):

        self.__sysname = sysname
        self.__pins = None
        self.__connected = False
        self.__sdpath = None
        self.__resp_921600 = False
        self.__serial = None
        self.__kill_ppp_ok = False
        self.__modem_speed = None
        self.__speed_detected = False

        if 'GPy' in self.__sysname:
            self.__pins = ('P5', 'P98', 'P7', 'P99')
        else:
            self.__pins = ('P20', 'P18', 'P19', 'P17')


    def special_print(self, msg, flush=None, end='\n'):
        if 'FiPy' in self.__sysname or 'GPy' in self.__sysname:
            print(msg, end=end)
        else:
            print(msg, flush=flush, end=end)

    def read_rsp(self, size=None, timeout=-1):
        time.sleep(.25)
        if timeout < 0:
            timeout = 20000
        elif timeout is None:
            timeout = 0
        if 'FiPy' in self.__sysname or 'GPy' in self.__sysname:
            while not self.__serial.any() and timeout > 0:
                time.sleep_ms(1)
                timeout -= 1
        else:
            while self.__serial.in_waiting <= 0 and timeout > 0:
                time.sleep(0.001)
                timeout -= 1

        if size is not None:
            rsp = self.__serial.read(size)
        else:
            rsp = self.__serial.read()
        if rsp is not None:
            return rsp
        else:
            return b''

    def print_pretty_response(self, rsp, flush=False, prefix=None):
        if prefix is not None: self.special_print(prefix, flush=flush, end=' ')
        lines = rsp.decode('ascii').split('\r\n')
        for line in lines:
            if 'OK' not in line and line!='':
                self.special_print(line, flush=flush)


    def return_pretty_response(self, rsp):
        ret_str = ''
        lines = rsp.decode('ascii').split('\r\n')
        for line in lines:
            if 'OK' not in line:
                ret_str += line
        return ret_str

    def return_upgrade_response(self, rsp):
        pretty = self.return_pretty_response(rsp)
        if "+SMUPGRADE:" in pretty:
            try:
                return pretty.split(':')[1].strip()
            except:
                pass
        return None

    def return_code(self, rsp, debug=False):
        ret_str = b''
        lines = rsp.decode('ascii').split('\r\n')
        for line in lines:
            if 'OK' not in line and len(line) >0:
                try:
                    if debug: print('Converting response: {} to int...'.format(line))
                    return int(line)
                except:
                    pass
        raise OSError('Could not decode modem state')


    def wait_for_modem(self, send=True, expected=b'OK', echo_char=None):
        rsp = b''
        start = time.time()
        while True:
            if send:
                self.__serial.write(b"AT\r\n")
            r = self.read_rsp(size=(len(expected) + 4), timeout=50)
            if r:
                rsp += r
            if expected in rsp:
                if echo_char is not None:
                    print()
                break
            else:
                if echo_char is not None:
                    self.special_print(echo_char, end='', flush=True)
                time.sleep(0.5)
            if time.time() - start >= 300:
                raise OSError('Timeout waiting for modem to respond!')

    def __check_file(self, file_path, debug=False):
        if 'FiPy' in self.__sysname or 'GPy' in self.__sysname:
            if file_path[0] == '/' and not 'flash' in file_path and not file_path.split('/')[1] in os.listdir('/'):
                if self.__sdpath is None:
                    self.__sdpath = file_path.split('/')[1]
                    try:
                        sd = SD()
                        time.sleep(0.5)
                        os.mount(sd, '/{}'.format(self.__sdpath))
                    except Exception as ex:
                        print('Unable to mount SD card!')
                        return False
                else:
                    print('SD card already mounted on {}!'.format(self.__sdpath))
                    return False
        try:
            size = os.stat(file_path)[6]
            if debug: print('File {} has size {}'.format(file_path, size))
            return True
        except Exception as ex:
            print('Exception when checking file {}... wrong file name?'.format(file_path))
            print('{}'.format(ex))
            return False
        return False


    def check_files(self, ffile, mfile=None, debug=False):
        if mfile is not None:
            if self.__check_file(mfile, debug):
                return self.__check_file(ffile, debug)
            else:
                return False
        else:
            return self.__check_file(ffile, debug)


    def __check_resp(self, resp, kill_ppp=False):
        if resp is not None:
            self.__resp_921600 = b'OK' in resp or b'ERROR' in resp
            self.__kill_ppp_ok = self.__kill_ppp_ok or (kill_ppp and b'OK' in resp)

    def __hangup_modem(self, delay, debug):
        self.__serial.read()
        if not self.__kill_ppp_ok:
            self.__serial.write(b"+++")
            time.sleep_ms(1150)
            resp = self.__serial.read()
            if debug: print('Response (+++ #1): {}'.format(resp))
            self.__check_resp(resp, True)
        self.__serial.write(b"AT\r\n")
        time.sleep_ms(250)
        resp = self.__serial.read()
        if debug: print('Response (AT #1) {}'.format(resp))
        self.__check_resp(resp)
        if resp is not None:
            if b'OK' not in resp and not self.__kill_ppp_ok:
                self.__serial.write(b"AT\r\n")
                time.sleep_ms(250)
                resp = self.__serial.read()
                if debug: print('Response (AT #2) {}'.format(resp))
                self.__check_resp(resp)
                if resp is not None and b'OK' in resp:
                    return True
                self.__serial.write(b"+++")
                time.sleep_ms(1150)
                resp = self.__serial.read()
                if debug: print('Response (+++ #2): {}'.format(resp))
                self.__check_resp(resp, True)
            if resp is not None and b'OK' in resp:
                self.__serial.write(b"AT\r\n")
                time.sleep_ms(250)
                resp = self.__serial.read()
                if debug: print('Response (AT #2) {}'.format(resp))
                self.__check_resp(resp)
                if resp is not None and b'OK' in resp:
                    return True
        return False


    def detect_modem_state(self, retry=5, initial_delay=1000, hangup=True, debug=False):
        count = 0
        self.__serial = UART(1, baudrate=921600, pins=self.__pins, timeout_chars=1)
        self.__modem_speed = 921600
        self.__serial.read()
        while count < retry:
            count += 1
            delay = initial_delay * count
            if debug: print("The current delay is {}".format(delay))
            self.__serial = UART(1, baudrate=921600, pins=self.__pins, timeout_chars=10)
            self.__modem_speed = 921600
            #if True:
            if hangup and self.__hangup_modem(initial_delay, debug):
                self.__speed_detected = True
                self.__serial.write(b"AT+SMOD?\r\n")
                time.sleep_ms(delay)
                resp = self.__serial.read()
                if debug: print('Response (AT+SMOD?) {}'.format(resp))
                try:
                    return self.return_code(resp, debug)
                except:
                    pass
            else:
                self.__modem_speed = 921600
                self.__serial = UART(1, baudrate=921600, pins=self.__pins, timeout_chars=1)
                self.__serial.read()
                self.__serial.write(b"AT\r\n")
                time.sleep_ms(delay)
                resp = self.__serial.read()
                self.__check_resp(resp)
                if debug: print('Response (AT #3) {}'.format(resp))
                if resp is not None and b'OK' in resp:
                    self.__speed_detected = True
                    self.__serial.write(b"AT+SMOD?\r\n")
                    time.sleep_ms(delay)
                    resp = self.__serial.read()
                    try:
                        if debug: print('Response (AT+SMOD?) {}'.format(resp))
                        return self.return_code(resp, debug)
                    except:
                        pass
                self.__serial.write(b"AT\r\n")
                time.sleep_ms(delay)
                resp = self.__serial.read()
                self.__check_resp(resp)
                if debug: print('Response (AT #4) {}'.format(resp))
                if resp is not None and b'OK' in resp:
                    self.__speed_detected = True
                    self.__serial.write(b"AT+SMOD?\r\n")
                    time.sleep_ms(delay)
                    resp = self.__serial.read()
                    try:
                        return self.return_code(resp, debug)
                        if debug: print('Response (AT+SMOD?) {}'.format(resp))
                    except:
                        pass
                else:
                    if not self.__resp_921600:
                        self.__modem_speed = 115200
                        self.__serial = UART(1, baudrate=115200, pins=self.__pins, timeout_chars=10)
                        self.__serial.write(b"AT\r\n")
                        time.sleep_ms(delay)
                        resp = self.__serial.read()
                        if debug: print('Response (AT #1 @ 115200) {}'.format(resp))
                        if resp is not None and b'OK' in resp:
                            self.__speed_detected = True
                            self.__serial.write(b"AT+SMOD?\r\n")
                            time.sleep_ms(delay)
                            resp = self.__serial.read()
                            try:
                                if debug: print('Response (AT+SMOD?) {}'.format(resp))
                                return self.return_code(resp, debug)
                            except:
                                pass
                        self.__serial.write(b"AT\r\n")
                        time.sleep_ms(delay)
                        resp = self.__serial.read()
                        if debug: print('Response (AT #2 @ 115200) {}'.format(resp))
                        if resp is not None and b'OK' in resp:
                            self.__speed_detected = True
                            self.__serial.write(b"AT+SMOD?\r\n")
                            time.sleep_ms(delay)
                            resp = self.__serial.read()
                            try:
                                if debug: print('Response (AT+SMOD?) {}'.format(resp))
                                return self.return_code(resp, debug)
                            except:
                                pass
        return None

    def get_imei(self):
        self.__serial = UART(1, baudrate=921600, pins=self.__pins, timeout_chars=10)
        self.__serial.write(b"AT+CGSN\r\n")
        time.sleep(.5)
        imei_val = self.read_rsp(2000)
        return self.return_pretty_response(imei_val)


    def __get_power_warning(self):
        return "<<<=== DO NOT DISCONNECT POWER ===>>>"

    def __get_wait_msg(self, load_fff=True):
        if not self.__wait_msg:
            self.__wait_msg = True
            if load_fff:
                return "Waiting for modem to finish the update...\nThis might take several minutes!\n" + self.__get_power_warning()
            else:
                return "Waiting for modem to finish the update...\n" + self.__get_power_warning()
        return None



    def __run(self, file_path=None, baudrate=921600, port=None, resume=False, load_ffh=False, mirror=False, switch_ffh=False, bootrom=False, rgbled=0x050505, debug=False, pkgdebug=False, atneg=True, max_try=10, direct=True, atneg_only=False, info_only=False, expected_smod=None, verbose=False, load_fff=False, mtools=False):
        self.__wait_msg = False
        mirror = True if atneg_only else mirror
        recover = True if atneg_only else load_ffh
        resume = True if mirror or recover or atneg_only or info_only else resume
        verbose = True if debug else verbose
        load_fff = False if bootrom and switch_ffh else load_fff
        target_baudrate = baudrate
        baudrate = self.__modem_speed if self.__speed_detected else baudrate
        if debug: print('mirror? {}  recover? {}  resume? {}  direct? {}  atneg_only? {} bootrom? {} load_fff? {}'.format(mirror, recover, resume, direct, atneg_only, bootrom, load_fff))
        if debug: print('baudrate: {} target_baudrate: {}'.format(baudrate, target_baudrate))
        abort = True
        external = False
        self.__serial = None

        if 'FiPy' in self.__sysname or 'GPy' in self.__sysname:

            self.__serial = UART(1, baudrate=115200 if recover and not self.__speed_detected else baudrate, pins=self.__pins, timeout_chars=100)
            self.__serial.read()
        else:
            if port is None:
                raise ValueError('serial port not specified')
            if debug: print('Setting port {}'.format(port))
            external = True
            br = 115200 if recover and not direct else baudrate
            if debug: print('Setting baudrate to {}'.format(br))
            self.__serial = serial.Serial(port, br, bytesize=serial.EIGHTBITS, timeout=1 if info_only else 0.1)
            self.__serial.reset_input_buffer()
            self.__serial.reset_output_buffer()

        if info_only:
            self.__serial.read()
            self.__serial.write(b'AT\r\n')
            self.__serial.write(b'AT\r\n')
            self.__serial.read()
            self.__serial.write(b"AT+CGSN\r\n")
            time.sleep(.5)
            shimei = self.read_rsp(2000)
            if verbose:
                self.__serial.write(b"AT!=\"showver\"\r\n")
            else:
                self.__serial.write(b"ATI1\r\n")
            time.sleep(.5)
            shver = self.read_rsp(2000)
            if shver is not None:
                self.print_pretty_response(shver)
            if shimei is not None:
                self.print_pretty_response(shimei, prefix='\nIMEI:')
            return True

        if debug: print('Initial prepartion complete...')

        if not mirror:
            if bootrom:
                if debug: print('Loading built-in recovery bootrom...')
                try:
                    # try compressed bootrom first
                    from sqnsbrz import bootrom
                except:
                    # fallback to uncompressed
                    from sqnsbr import bootrom
                blob = bootrom()
                blobsize = blob.get_size()
            else:
                if debug: print('Loading {}'.format(file_path))
                blobsize = os.stat(file_path)[6]
                if blobsize < 128:
                    print('Firmware file is too small!')
                    reconnect_uart()
                    sys.exit(1)
                if blobsize > 4194304:
                    if load_fff:
                        print("Firmware file is too big to load via FFF method. Using ON_THE_FLY")
                    load_fff = False
                blob = open(file_path, "rb")

        if not load_ffh:
            if not self.wakeup_modem(baudrate, port, 10, 1, debug):
                return False

        if (not resume) or mtools:

            # bind to AT channel
            self.__serial.write(b"AT+BIND=AT\r\n")
            time.sleep(.5)
            response = self.read_rsp(size=100)
            if debug: print("AT+BIND=AT returned {}".format(response))

            # disable echo
            self.__serial.write(b"ATE0\r\n")
            time.sleep(.5)
            response = self.read_rsp(size=100)
            if debug: print("ATE0 returned {}".format(response))

            self.__serial.read()
            if debug: print('Entering upgrade mode...')

            if verbose: print("Sending AT+SMLOG?")
            self.__serial.write(b'AT+SMLOG?\r\n')
            response = self.read_rsp(size=100)
            if verbose: print("AT+SMLOG? returned {}".format(response))

            self.__serial.write(b"AT+SMOD?\r\n")
            response = self.return_pretty_response(self.read_rsp(size=7))
            if debug: print("AT+SMOD? returned {}".format(response))

            if verbose: print('Sending AT+FSRDFILE="/fs/crashdump"')
            self.__serial.write(b'AT+FSRDFILE="/fs/crashdump"\r\n')
            response = self.read_rsp(size=100)
            if verbose: print('AT+FSRDFILE="/fs/crashdump" returned {}'.format(response))
            self.__serial.read()

            self.__serial.write(b"AT+SQNSUPGRADENTF=\"started\"\r\n")
            response = self.read_rsp(size=100)
            if verbose: print('AT+SQNSUPGRADENTF="started" returned {}'.format(response))
            self.wait_for_modem()

            if verbose: print('Sending AT+SQNWL="sqndcc",2')
            self.__serial.write(b'AT+SQNWL="sqndcc",2\r\n')
            response = self.read_rsp(size=100)
            if verbose: print('AT+SQNWL="sqndcc",2 returned {}'.format(response))
            self.__serial.read(100)

            if verbose: print("Sending AT+CFUN=4")
            self.__serial.write(b'AT+CFUN=4\r\n')
            response = self.read_rsp(size=100)
            if verbose: print("AT+CFUN=4 returned {}".format(response))
            self.__serial.read(100)

            if not (load_fff or mtools):
                self.__serial.write(b"AT+SMSWBOOT=3,1\r\n")
                resp = self.read_rsp(100)
                if debug: print('AT+SMSWBOOT=3,1 returned: {}'.format(resp))
                if b'ERROR' in resp:
                    time.sleep(5)
                    self.__serial.write(b"AT+SMSWBOOT=3,0\r\n")
                    resp = self.read_rsp(100)
                    if debug: print('AT+SMSWBOOT=3,0 returned: {}'.format(resp))
                    if b'OK' in resp:
                        self.__serial.write(b"AT^RESET\r\n")
                        resp = self.read_rsp(100)
                        if debug: print('AT^RESET returned: {}'.format(resp))
                    else:
                        print('Received ERROR from AT+SMSWBOOT=3,1! Aborting!')
                        reconnect_uart()
                        sys.exit(1)
                time.sleep(3)
                resp = self.__serial.read()
                if debug: print("Response after reset: {}".format(resp))
                self.wait_for_modem()
                self.__serial.write(b"AT\r\n")

                if verbose: print("Sending AT+CFUN=4")
                self.__serial.write(b'AT+CFUN=4\r\n')
                response = self.read_rsp(size=100)
                if verbose: print("AT+CFUN=4 returned {}".format(response))

                if verbose: print("Sending AT+SMLOG?")
                self.__serial.write(b'AT+SMLOG?\r\n')
                response = self.read_rsp(size=100)
                if verbose: print("AT+SMLOG? returned {}".format(response))

                if verbose: print('Sending AT+FSRDFILE="/fs/crashdump"')
                self.__serial.write(b'AT+FSRDFILE="/fs/crashdump"\r\n')
                response = self.read_rsp(size=100)
                if verbose: print('AT+FSRDFILE="/fs/crashdump" returned {}'.format(response))
                self.__serial.read()


        else:
            self.__serial.read(100)
            if debug: print('Entering recovery mode')

            self.__serial.write(b"AT+SMOD?\r\n")
            response = self.return_pretty_response(self.read_rsp(size=7))
            self.__serial.read(100)
            if debug: print("AT+SMOD? returned {}".format(response))

        time.sleep(1)
        self.__serial.read()

        if (not recover) and (not direct):
            if mirror:
                time.sleep(.5)
                self.__serial.read(100)
                print('Going into MIRROR mode... please close this terminal to resume the upgrade via UART')
                self.uart_mirror(rgbled)

            elif bootrom:
                if verbose: print('Starting STP')
            else:
                if verbose:
                    if load_fff:
                        print('Starting STP [FFF]')
                    else:
                        print('Starting STP ON_THE_FLY')

            self.__serial.read(100)

            if load_fff:
                if debug: print("Sending AT+SMSTPU")
                self.__serial.write(b'AT+SMSTPU\r\n')
            else:
                if debug: print("Sending AT+SMSTPU=\"ON_THE_FLY\"")
                self.__serial.write(b'AT+SMSTPU=\"ON_THE_FLY\"\r\n')

            response = self.read_rsp(size=4)
            if response != b'OK\r\n' and response != b'\r\nOK' and response != b'\nOK':
                raise OSError("Invalid answer '%s' from the device" % response)
                blob.close()

            self.__serial.read()
        elif recover and (not direct):
            if atneg:
                result = self.at_negotiation(baudrate, port, max_try, mirror, atneg_only, debug, target_baudrate)
                if result:
                    baudrate = target_baudrate
                    self.__modem_speed = target_baudrate
                    self.__speed_detected = True
                    if atneg_only:
                        return True
                    if mirror:
                        time.sleep(.5)
                        self.__serial.read(100)
                        print('Going into MIRROR mode... please close this terminal to resume the upgrade via UART')
                        self.uart_mirror(rgbled)
                    else:
                        self.__serial.write(b"AT+STP\n")
                        response = self.read_rsp(size=6)
                        if not b'OK' in response:
                            print('Failed to start STP mode!')
                            reconnect_uart()
                            sys.exit(1)
                else:
                    print('AT auto-negotiation failed! Exiting.')
                    return False
        else:
            if debug: print('Starting STP mode...')
            self.__serial.write(b"AT+STP\n")
            response = self.read_rsp(size=6)
            if not b'OK' in response:
                print('Failed to start STP mode!')
                reconnect_uart()
                sys.exit(1)

        try:
            if debug:
                if verbose: print('Starting STP code upload')
            if stp.start(blob, blobsize, self.__serial, baudrate, AT=False, debug=debug, pkgdebug=pkgdebug):
                blob.close()
                self.__serial.read()
                if switch_ffh:
                    if verbose: print('Bootrom updated successfully, switching to recovery mode')
                    abort = False
                elif load_ffh:
                    if not self.wakeup_modem(baudrate, port, 100, 1, debug,'Waiting for updater to load...'):
                        return False
                    if verbose: print('Upgrader loaded successfully, modem is in update mode')
                    return True
                else:
                    if verbose: print('Code download done, returning to user mode')
                    abort = recover
            else:
                blob.close()
                print('Code download failed, aborting!')
                return False
        except:
            blob.close()
            print('Code download failed, aborting!')
            abort = True

        time.sleep(1.5)

        if not abort:
            self.__serial.read()
            if switch_ffh:
                self.__serial.write(b"AT+SMSWBOOT=0,1\r\n")
                resp = self.read_rsp(100)
                if debug: print("AT+SMSWBOOT=0,1 returned {}".format(resp))
                if b"ERROR" in resp:
                    time.sleep(5)
                    self.__serial.write(b"AT+SMSWBOOT=0,0\r\n")
                    resp = self.read_rsp(100)
                    if debug: print('AT+SMSWBOOT=0,0 returned: {}'.format(resp))
                    if b'OK' in resp:
                        self.__serial.write(b"AT^RESET\r\n")
                        resp = self.read_rsp(100)
                        if debug: print('AT^RESET returned: {}'.format(resp))
                        return True
                    else:
                        print('Received ERROR from AT+SMSWBOOT=0,0! Aborting!')
                        return False
                return True
            else:
                if load_fff:
                    self.__serial.write(b"AT+SMUPGRADE\r\n")
                if not self.wakeup_modem(baudrate, port, 100, 1, debug, self.__get_wait_msg(load_fff=load_fff)):
                    print("Timeout while waiting for modem to finish updating!")
                    reconnect_uart()
                    sys.exit(1)

                start = time.time()
                while True:
                    self.__serial.read()
                    self.__serial.write(b"AT+SMUPGRADE?\r\n")
                    resp = self.read_rsp(1024)
                    if debug: print("AT+SMUPGRADE? returned {} [timeout: {}]".format(resp, time.time() - start))

                    if resp == b'\x00' or resp == b'':
                        time.sleep(2)

                    if b'No report' in resp or b'on-going' in resp:
                        time.sleep(1)

                    if b'success' in resp or b'fail' in resp:
                        break

                    if time.time() - start >= 300:
                        raise OSError('Timeout waiting for modem to respond!')

                self.__serial.write(b"AT+SMSWBOOT?\r\n")
                resp = self.read_rsp(100)
                if debug: print("AT+SMSWBOOT? returned {}".format(resp))
                start = time.time()
                while (b"RECOVERY" not in resp) and (b"FFH" not in resp) and (b"FFF" not in resp):
                    if debug: print("Timeout: {}".format(time.time() - start))
                    if time.time() - start >= 300:
                        reconnect_uart()
                        raise OSError('Timeout waiting for modem to respond!')
                    time.sleep(2)
                    if not self.wakeup_modem(baudrate, port, 100, 1, debug, self.__get_wait_msg(load_fff=load_fff)):
                        reconnect_uart()
                        raise OSError('Timeout while waiting for modem to finish updating!')
                    self.__serial.read()
                    self.__serial.write(b"AT+SMSWBOOT?\r\n")
                    resp = self.read_rsp(100)
                    if debug: print("AT+SMSWBOOT? returned {}".format(resp))
                self.__serial.read()
                self.__serial.write(b"AT+SMUPGRADE?\r\n")
                resp = self.read_rsp(1024)
                if debug: print("AT+SMUPGRADE? returned {}".format(resp))
                sqnup_result = self.return_upgrade_response(resp)
                if debug: print('This is my result: {}'.format(sqnup_result))
                if 'success' in sqnup_result:
                    if not load_fff:
                        self.special_print('Resetting.', end='', flush=True)
                        self.__serial.write(b"AT+SMSWBOOT=1,1\r\n")
                        if debug: print("AT+SMSWBOOT=1,1 returned {}".format(resp))
                        if b"ERROR" in resp:
                            time.sleep(5)
                            self.__serial.write(b"AT+SMSWBOOT=1,0\r\n")
                            resp = self.read_rsp(100)
                            if debug: print('AT+SMSWBOOT=1,0 returned: {}'.format(resp))
                            if b'OK' in resp:
                                self.__serial.write(b"AT^RESET\r\n")
                                resp = self.read_rsp(100)
                                if debug: print('AT^RESET returned: {}'.format(resp))
                                return True
                            else:
                                print('Received ERROR from AT+SMSWBOOT=1,0! Aborting!')
                                return False
                        self.wait_for_modem(send=False, echo_char='.', expected=b'+SYSSTART')

                elif sqnup_result is not None:
                    print('Upgrade failed with result {}!'.format(sqnup_result))
                    print('Please check your firmware file(s)')
                else:
                    print("Invalid response after upgrade... aborting.")
                    reconnect_uart()
                    sys.exit(1)

                self.__serial.write(b"AT\r\n")
                self.__serial.write(b"AT\r\n")
                time.sleep(0.5)

                if 'success' in sqnup_result:
                    if verbose: print('Sending AT+SQNSUPGRADENTF="success"')
                    self.__serial.write(b"AT+SQNSUPGRADENTF=\"success\"\r\n")
                    resonse = self.read_rsp(100)
                    if verbose: print('AT+SQNSUPGRADENTF="success" returned {}'.format(response))
                    time.sleep(.25)
                    if verbose: print('Sending AT+FSRDFILE="/fs/crashdump"')
                    self.__serial.write(b'AT+FSRDFILE="/fs/crashdump"\r\n')
                    resonse = self.read_rsp(100)
                    if verbose: print('AT+FSRDFILE="/fs/crashdump" returned {}'.format(response))
                    self.__serial.read()
                    return True
                elif sqnup_result is None:
                    print('Modem upgrade was unsucessfull. Please check your firmware file(s)')
        return False

    def __check_br(self, br_only=False, verbose=False, debug=False):
        old_br = None
        old_sw = None
        if debug: print("Checking bootrom & application")
        self.__serial.write(b"AT!=\"showver\"\r\n")
        time.sleep(.5)
        shver = self.read_rsp(2000)
        if shver is not None:
            for line in shver.decode('ascii').split('\n'):
                if debug: print('Checking line {}'.format(line))
                if "Bootloader0" in line:
                    old_br = "[33080]" in line
                    if debug: print("old_br: {}".format(old_br))

                if "Software" in line:
                    old_sw = "[33080]" in line
                    if debug: print("old_sw: {}".format(old_sw))
        if old_br is None or old_sw is None:
            if debug: print("Returning: None")
            return None
        if old_br and (br_only or not old_sw):
            if debug: print("Returning: True")
            return True
        if debug: print("Returning: False")
        return False



    def wakeup_modem(self, baudrate, port, max_try, delay, debug, msg='Attempting AT wakeup...'):
        if 'FiPy' in self.__sysname or 'GPy' in self.__sysname:
            self.__serial = UART(1, baudrate=baudrate, pins=self.__pins, timeout_chars=10)
        MAX_TRY = max_try
        count = 0
        if msg is not None:
            if debug:
                print(msg + ' [{}]'.format(baudrate))
            else:
                print(msg)

        self.__serial.read()
        self.__serial.write(b"AT\r\n")
        response = self.read_rsp(size=25)
        if debug: print('{}'.format(response))
        while (not b'OK' in response) and (count < MAX_TRY):
            count = count + 1
            if debug: print('count={}'.format(count))
            time.sleep(delay)
            self.__serial.read()
            self.__serial.write(b"AT\r\n")
            response = self.read_rsp(size=25)
            if debug: print('{}'.format(response))
        if 'FiPy' in sysname or 'GPy' in sysname:
            self.__serial = UART(1, baudrate=baudrate, pins=self.__pins, timeout_chars=100)
        return count < MAX_TRY

    def at_negotiation(self, baudrate, port, max_try, mirror, atneg_only, debug, target_baudrate):
        MAX_TRY = max_try
        count = 0
        if debug:
            print('Attempting AT auto-negotiation... with baudrate {} and target_baudrate {}'.format(baudrate, target_baudrate))
        else:
            print('Attempting AT auto-negotiation...')
        self.__serial.write(b"AT\r\n")
        response = self.read_rsp(size=20)
        if debug: print('{}'.format(response))
        while (not b'OK' in response) and (count < MAX_TRY):
            count = count + 1
            if debug: print('count={}'.format(count))
            time.sleep(1)
            self.__serial.read()
            self.__serial.write(b"AT\r\n")
            response = self.read_rsp(size=20)
            if debug: print('{}'.format(response))
        if b'OK' in response:
            self.__serial.read()
            cmd = "AT+IPR=%d\n"%target_baudrate
            if debug: print('Setting baudrate to {}'.format(target_baudrate))
            self.__serial.write(cmd.encode())
            response = self.read_rsp(size=6)
            if debug: print('{}'.format(response))
            if b'OK' in response:
                self.__modem_speed = target_baudrate
                self.__speed_detected =  True
                if atneg_only:
                    return True
                if 'FiPy' in self.__sysname or 'GPy' in self.__sysname:
                    self.__serial = UART(1, baudrate=target_baudrate, pins=self.__pins, timeout_chars=100)
                else:
                    self.__serial = None
                    self.__serial = serial.Serial(port, target_baudrate, bytesize=serial.EIGHTBITS, timeout=0.1)
                    self.__serial.reset_input_buffer()
                    self.__serial.reset_output_buffer()
                    self.__serial.flush()
                self.__serial.read()
                if debug: print('Checking SMOD')
                self.__serial.write(b"AT+SMOD?\r\n")
                response = self.read_rsp(size=1)
                if b'0' in response:
                    if debug: print("AT+SMOD? returned {}".format(response))
                    self.__serial.read()
                    return True
                else:
                    print('ERROR in AT+SMOD returned {}'.format(response))
                    return False
            else:
                print('ERROR in AT+IPR={} returned {}'.format(target_baudrate, response))
                return False
        else:
            print('ERROR sending AT command... no response? {}'.format(response))
            return False
        time.sleep(1)
        return True

    def uart_mirror(self, color):
        import pycom
        pycom.heartbeat(False)
        time.sleep(.5)
        pycom.rgbled(color)
        LTE.modem_upgrade_mode()

    def success_message(self, port=None, verbose=False, debug=False):
        print("Your modem has been successfully updated.")
        print("Here is the current firmware version:\n")
        self.show_info(port=port, verbose=verbose, debug=debug)

    def upgrade(self, ffile, mfile=None, baudrate=921600, retry=False, resume=False, debug=False, pkgdebug=False, verbose=False, load_fff=True, load_only=False, mtools=False):
        success = True
        if not retry and mfile is not None:
            if resume or self.__check_br(br_only=True, verbose=verbose, debug=debug):
                success = False
                success = self.__run(bootrom=True, resume=resume, switch_ffh=True, direct=False, debug=debug, pkgdebug=pkgdebug, verbose=verbose)
                time.sleep(1)
            else:
                print('{} is not required. Resumining normal upgrade.'.format(mfile))
                mfile=None
                success=True
        if debug: print('Success1? {}'.format(success))
        if success:
            if mfile is not None:
                success = False
                success = self.__run(file_path=mfile, load_ffh=True, direct=False, baudrate=baudrate, debug=debug, pkgdebug=pkgdebug, verbose=verbose)
                time.sleep(1)
                if load_only:
                    return True
            else:
                success = True
        else:
            print('Unable to upgrade bootrom.')
        if debug: print('Success2? {}'.format(success))
        if success:
            if self.__run(file_path=ffile, resume=True if mfile is not None else resume, baudrate=baudrate, direct=False, debug=debug, pkgdebug=pkgdebug, verbose=verbose, load_fff=False if mfile else load_fff, mtools=mtools):
                if self.__check_br(verbose=verbose, debug=debug):
                    self.__run(bootrom=True, debug=debug, direct=False, pkgdebug=pkgdebug, verbose=verbose, load_fff=True)
                self.success_message(verbose=verbose, debug=debug)
        else:
            print('Unable to load updater from {}'.format(mfile))

    def upgrade_uart(self, ffh_mode=False, mfile=None, retry=False, resume=False, color=0x050505, debug=False, pkgdebug=False, verbose=False, load_fff=True):
        success = False
        try:
            success = hasattr(LTE,'modem_upgrade_mode')
        except:
            success = False
        if not success:
            print('Firmware does not support LTE.modem_upgrade_mode()!')
            reconnect_uart()
            sys.exit(1)
        print('Preparing modem for upgrade...')
        if not retry and ffh_mode:
            success = False
            if self.__check_br(verbose=verbose, debug=debug):
                success = self.__run(bootrom=True, resume=resume, switch_ffh=True, direct=False, debug=debug, pkgdebug=pkgdebug, verbose=verbose)
                time.sleep(1)
            else:
                print('FFH mode is not necessary... ignoring!')
                print('Do not specify updater.elf when updating!')
                mfile = None
                ffh_mode = False
                success = True
        if success:
            if mfile is not None:
                success = False
                success = self.__run(file_path=mfile, load_ffh=True, direct=False, debug=debug, pkgdebug=pkgdebug, verbose=verbose)
                if debug: print('Success2? {}'.format(success))
                if success:
                    self.__run(mirror=True, load_ffh=False, direct=False, rgbled=color, debug=debug, verbose=verbose)
                else:
                    print('Unable to load updater from {}'.format(mfile))
            else:
                self.__run(mirror=True, load_ffh=ffh_mode, direct=False, rgbled=color, debug=debug, verbose=verbose)
        else:
            print('Unable to upgrade bootrom.')

    def show_info(self, port=None, debug=False, verbose=False):
        self.__run(port=port, debug=debug, info_only=True, verbose=verbose)

    def upgrade_ext(self, port, ffile, mfile, resume=False, debug=False, pkgdebug=False, verbose=False, load_fff=True):
        success = True
        if mfile is not None:
            success = False
            success = self.__run(file_path=mfile, load_ffh=True, port=port, debug=debug, pkgdebug=pkgdebug, verbose=verbose)
        if success:
            if self.__run(file_path=ffile, resume=True if mfile is not None else resume, direct=False, port=port, debug=debug, pkgdebug=pkgdebug, verbose=verbose, load_fff=load_fff):
                self.success_message(port=port, verbose=verbose, debug=debug)
        else:
            print('Unable to load updater from {}'.format(mfile))

def detect_error():
    print('Could not detect your modem!')
    print('Please try to power off your device and restart in safeboot mode.')
    reconnect_uart()
    sys.exit(1)

def print_welcome():
    print('<<< Welcome to the SQN3330 firmware updater [{}] >>>'.format(VERSION))
    if release is not None:
        print('>>> {} with firmware version {}'.format(sysname,release))



if 'FiPy' in sysname or 'GPy' in sysname:

    def load(mfile, baudrate=921600, verbose=False, debug=False, hangup=False):
        print_welcome()
        sqnup = sqnsupgrade()
        if sqnup.check_files(mfile, None, debug):
            state = sqnup.detect_modem_state(debug=debug, hangup=hangup)
            if debug: print('Modem state: {}'.format(state))
            if state is None:
                detect_error()
            elif state == 0:
                sqnup.upgrade(ffile=None, mfile=mfile, baudrate=baudrate, retry=True, resume=False, debug=debug, pkgdebug=False, verbose=verbose, load_fff=False, load_only=True)
            elif state == -1:
                detect_error()
            else:
                print('Modem must be in recovery mode!')
        reconnect_uart()

    def run(ffile, mfile=None, baudrate=921600, verbose=False, debug=False, load_fff=True, hangup=True):
        print_welcome()
        retry = False
        resume = False
        mtools = False
        sqnup = sqnsupgrade()
        if sqnup.check_files(ffile, mfile, debug):
            state = sqnup.detect_modem_state(debug=debug, hangup=hangup)
            if debug: print('Modem state: {}'.format(state))
            if state is None:
                detect_error()
            elif state == 0:
                retry = True
                if mfile is None:
                    print('Your modem is in recovery mode. Please specify updater.elf file')
                    reconnect_uart()
                    sys.exit(1)
            elif state == 4:
                resume = True
            elif state == 1:
                mtools = True
            elif state == -1:
                detect_error()
            sqnup.upgrade(ffile=ffile, mfile=mfile, baudrate=baudrate, retry=retry, resume=resume, debug=debug, pkgdebug=False, verbose=verbose, load_fff=load_fff, mtools=mtools)
        reconnect_uart()

    def uart(ffh_mode=False, mfile=None, color=0x050505, verbose=False, debug=False, hangup=True):
        print_welcome()
        retry = False
        resume = False
        import pycom
        state = None
        sqnup = sqnsupgrade()
        if verbose: print('Trying to detect modem state...')
        state = sqnup.detect_modem_state(debug=debug, hangup=hangup)
        if debug: print('Modem state: {}'.format(state))

        if state is None:
            detect_error()
        elif state == 0:
            print('Your modem is in recovery mode. You will need to use firmware.dup and updater.elf file to upgrade.')
            retry = True
            ffh_mode = True
        elif state == 4:
            resume = True
        elif state == -1:
            detect_error()
        sqnup.upgrade_uart(ffh_mode, mfile, retry, resume, color, debug, False, verbose)

    def info(verbose=False, debug=False, hangup=True):
        print_welcome()
        import pycom
        state = None
        sqnup = sqnsupgrade()
        if verbose: print('Trying to detect modem state...')
        state = sqnup.detect_modem_state(debug=debug, hangup=hangup)
        if debug: print('Modem state: {}'.format(state))

        if state is not None:
            if state == 2:
                print('Your modem is in application mode. Here is the current version:')
                sqnup.show_info(verbose=verbose, debug=debug)
            elif state == 1:
                print('Your modem is in mTools mode.')
            elif state == 0:
                print('Your modem is in recovery mode! Use firmware.dup and updater.elf to flash new firmware.')
            elif state == 4:
                print('Your modem is in upgrade mode! Use firmware.dup to flash new firmware.')
            elif state == -1:
                print('Cannot determine modem state!')
            if hasattr(pycom, 'lte_modem_en_on_boot') and verbose:
                print('LTE autostart {}.'.format('enabled' if pycom.lte_modem_en_on_boot() else 'disabled'))
        else:
            print('Cannot determine modem state!')
        reconnect_uart()

    def imei(verbose=False, debug=False, retry=5, hangup=False):
        sqnup = sqnsupgrade()
        state = sqnup.detect_modem_state(debug=debug, hangup=hangup, retry=retry)
        return sqnup.get_imei() if state == 2 else None

    def state(verbose=False, debug=False, retry=5, hangup=False):
        sqnup = sqnsupgrade()
        return sqnup.detect_modem_state(debug=debug, hangup=hangup, retry=retry)

else:
    def run(port, ffile, mfile=None, resume=False, debug=False, verbose=False, load_fff=True):
        print_welcome()
        sqnup = sqnsupgrade()
        if sqnup.check_files(ffile, mfile, debug):
            sqnup.upgrade_ext(port=port, ffile=ffile, mfile=mfile, resume=resume, debug=debug, pkgdebug=False, verbose=verbose, load_fff=load_fff)

    def version(port, verbose=False, debug=False):
        sqnup = sqnsupgrade()
        sqnup.show_info(port=port, debug=debug, verbose=verbose)
