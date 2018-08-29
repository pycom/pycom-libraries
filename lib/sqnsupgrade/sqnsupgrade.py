#!/usr/bin/env python
import struct
import time
import os
import sys
import sqnscrc as crc
import sqnstp as stp

try:
    sysname = os.uname().sysname
except:
    sysname = 'Windows'

if 'FiPy' in sysname or 'GPy' in sysname:
    from machine import UART
    from machine import SD
else:   # this is a computer
    import serial

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

class sqnsupgrade:

    global sysname

    def __init__(self):

        self.__sysname = sysname
        self.__pins = None
        self.__connected = False
        self.__sdpath = None

    def special_print(self, msg, flush=None, end='\n'):
        if 'FiPy' in self.__sysname or 'GPy' in self.__sysname:
            print(msg, end=end)
        else:
            print(msg, flush=flush, end=end)

    def read_rsp(self, size=None, timeout=-1):
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

    def print_pretty_response(self, rsp, flush=False):
        lines = rsp.decode('ascii').split('\r\n')
        for line in lines:
            if 'OK' not in line:
                self.special_print(line, flush=flush)


    def return_pretty_response(self, rsp):
        ret_str = ''
        lines = rsp.decode('ascii').split('\r\n')
        for line in lines:
            if 'OK' not in line:
                ret_str += line
        return ret_str

    def return_code(self, rsp):
        ret_str = b''
        lines = rsp.decode('ascii').split('\r\n')
        for line in lines:
            if 'OK' not in line:
                ret_str += line
        try:
            return int(ret_str)
        except:
            return -1


    def wait_for_modem(self, send=True, expected=b'OK'):
        rsp = b''
        while True:
            if send:
                self.__serial.write(b"AT\r\n")
            r = self.read_rsp(size=(len(expected) + 4), timeout=50)
            if r:
                rsp += r
            if expected in rsp:
                print()
                break
            else:
                self.special_print('.', end='', flush=True)
                time.sleep(0.5)

    def __check_file(self, file_path, debug=False):
        if 'FiPy' in self.__sysname or 'GPy' in self.__sysname:
            if file_path[0] == '/' and not 'flash' in file_path and not file_path.split('/')[1] in os.listdir('/'):
                if self.__sdpath is None:
                    self.__sdpath = file_path.split('/')[1]
                    sd = SD()
                    time.sleep(0.5)
                    os.mount(sd, '/{}'.format(self.__sdpath))
                else:
                    print('SD card already mounted on {}!'.format(self.__sdpath))
                    return False
        try:
            size = os.stat(file_path)[6]
            if debug: print('File {} has size {}'.format(file_path, size))
            return True
        except Exception as ex:
            print('Exception when checking file... wrong file name?')
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

    def detect_modem_state(self, retry=10, initial_delay=5):
        if 'FiPy' or 'GPy' in self.__sysname:

            if 'GPy' in self.__sysname:
                pins = ('P5', 'P98', 'P7', 'P99')
            else:
                pins = ('P20', 'P18', 'P19', 'P17')
        count = 0
        while count < retry:
            count += 1
            delay = initial_delay * count
            s = UART(1, baudrate=921600, pins=pins, timeout_chars=10)
            s.read()
            s.write(b"AT\r\n")
            time.sleep_ms(delay)
            resp = s.read()
            s.write(b"AT\r\n")
            time.sleep_ms(delay)
            resp = s.read()
            if resp is not None and b'OK' in resp:
                s.write(b"AT+SMOD?\r\n")
                time.sleep_ms(delay)
                resp = s.read()
                try:
                    return self.return_code(resp)
                except:
                    continue
            else:
                s = UART(1, baudrate=115200, pins=pins, timeout_chars=10)
                s.write(b"AT\r\n")
                time.sleep_ms(delay)
                resp = s.read()
                s.write(b"AT\r\n")
                time.sleep_ms(delay)
                resp = s.read()
                if resp is not None and b'OK' in resp:
                    s.write(b"AT+SMOD?\r\n")
                    time.sleep_ms(delay)
                    resp = s.read()
                    try:
                        return self.return_code(resp)
                    except:
                        continue


    def __run(self, file_path=None, baudrate=921600, port=None, resume=False, load_ffh=False, mirror=False, switch_ffh=False, bootrom=False, rgbled=0x050505, debug=False, pkgdebug=False, atneg=True, max_try=10, direct=True, atneg_only=False, version_only=False):
        mirror = True if atneg_only else mirror
        recover = True if atneg_only else load_ffh
        resume = True if mirror or recover or atneg_only or version_only else resume
        if debug: print('mirror? {}  recover? {}  resume? {}  direct? {}  atneg_only? {} bootrom? {} '.format(mirror, recover, resume, direct, atneg_only, bootrom))
        abort = True
        external = False
        self.__serial = None

        if 'FiPy' in self.__sysname or 'GPy' in self.__sysname:

            if 'GPy' in self.__sysname:
                self.__pins = ('P5', 'P98', 'P7', 'P99')
            else:
                self.__pins = ('P20', 'P18', 'P19', 'P17')

            self.__serial = UART(1, baudrate=115200 if recover else baudrate, pins=self.__pins, timeout_chars=100)
            self.__serial.read()
        else:
            if port is None:
                raise ValueError('serial port not specified')
            if debug: print('Setting port {}'.format(port))
            external = True
            br = 115200 if recover and not direct else baudrate
            if debug: print('Setting baudrate to {}'.format(br))
            self.__serial = serial.Serial(port, br, bytesize=serial.EIGHTBITS, timeout=1 if version_only else 0.1)
            self.__serial.reset_input_buffer()
            self.__serial.reset_output_buffer()

        if debug: print('Initial prepartion complete...')

        if version_only:
            self.__serial.read()
            self.__serial.write(b"AT!=\"showver\"\r\n")
            time.sleep(.5)
            shver = self.read_rsp(2000)
            if shver is not None:
                self.print_pretty_response(shver)
            return True

        if not mirror:
            if bootrom:
                if debug: print('Loading built-in recovery bootrom')
                from sqnsbr import bootrom
                blob = bootrom()
                blobsize = blob.get_size()
            else:
                if debug: print('Loading {}'.format(file_path))
                blobsize = os.stat(file_path)[6]
                blob = open(file_path, "rb")

        if not load_ffh:
            if not self.wakeup_modem(baudrate, port, 10, 1, debug):
                return False

        if not resume:

            # disable echo
            self.__serial.write(b"ATE0\r\n")
            response = self.read_rsp(size=6)

            self.__serial.read(100)
            if debug: print('Entering recovery mode')

            self.__serial.write(b"AT+SMOD?\r\n")
            response = self.return_pretty_response(self.read_rsp(size=7))
            self.__serial.read(100)
            if debug: print("AT+SMOD? returned {}".format(response))

            if not bootrom:
                self.__serial.write(b"AT+SMSWBOOT=3,1\r\n")
                time.sleep(2)
                self.wait_for_modem()
                self.__serial.write(b"AT\r\n")
                self.__serial.write(b"AT\r\n")

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
                print('Starting STP (DO NOT DISCONNECT POWER!!!)')

            else:
                print('Starting STP ON_THE_FLY')
            self.__serial.read(100)

            self.__serial.write(b'AT+SMSTPU=\"ON_THE_FLY\"\r\n')
            response = self.read_rsp(size=4)
            if response != b'OK\r\n' and response != b'\r\nOK' and response != b'\nOK':
                raise OSError("Invalid answer '%s' from the device" % response)
                blob.close()

            self.__serial.read()
        elif recover and (not direct):
            if atneg:
                result = self.at_negotiation(baudrate, port, max_try, mirror, atneg_only, debug)
                if result:
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
                sys.exit(1)

        try:
            if debug:
                print('Starting STP code upload')
            if stp.start(blob, blobsize, self.__serial, baudrate, AT=False, debug=debug, pkgdebug=pkgdebug):
                blob.close()
                if switch_ffh:
                    print('Bootrom updated successfully, switching to upgrade mode')
                    abort = False
                elif load_ffh:
                    if not self.wakeup_modem(baudrate, port, 100, 1, debug):
                        return False
                    print('Upgrader loaded successfully, modem is in upgrade mode')
                    return True
                else:
                    print('Code download done, returning to user mode')
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
                return True
            else:
                self.special_print('Resetting (DO NOT DISCONNECT POWER!!!).', end='', flush=True)
                self.__serial.write(b"AT+SMSWBOOT=1,1\r\n")
                self.wait_for_modem(send=False, expected=b'+SYSSTART')

                self.__serial.write(b"AT\r\n")
                self.__serial.write(b"AT\r\n")
                time.sleep(0.5)
                self.__serial.read()
                print('Upgrade completed!')
                print("Here's the current firmware version:")
                time.sleep(0.5)
                self.__serial.read()
                self.__serial.write(b"AT!=\"showver\"\r\n")
                time.sleep(.5)
                shver = self.read_rsp(2000)
                if shver is not None:
                    self.print_pretty_response(shver)
                return True
        return False

    def wakeup_modem(self, baudrate, port, max_try, delay, debug):
        if 'FiPy' in self.__sysname or 'GPy' in self.__sysname:
            self.__serial = UART(1, baudrate=baudrate, pins=self.__pins, timeout_chars=1)
        MAX_TRY = max_try
        count = 0
        print('Attempting AT wakeup...')
        self.__serial.read()
        self.__serial.write(b"AT\r\n")
        response = self.read_rsp(size=6)
        if debug: print('{}'.format(response))
        while (not b'OK' in response) and (count < MAX_TRY):
            count = count + 1
            if debug: print('count={}'.format(count))
            time.sleep(delay)
            self.__serial.read()
            self.__serial.write(b"AT\r\n")
            response = self.read_rsp(size=6)
            if debug: print('{}'.format(response))
        if 'FiPy' in sysname or 'GPy' in sysname:
            self.__serial = UART(1, baudrate=baudrate, pins=self.__pins, timeout_chars=100)
        return count < MAX_TRY

    def at_negotiation(self, baudrate, port, max_try, mirror, atneg_only, debug):
        MAX_TRY = max_try
        count = 0
        print('Attempting AT auto-negotiation...')
        self.__serial.write(b"AT\r\n")
        response = self.read_rsp(size=6)
        if debug: print('{}'.format(response))
        while (not b'OK' in response) and (count < MAX_TRY):
            count = count + 1
            if debug: print('count={}'.format(count))
            time.sleep(1)
            self.__serial.read()
            self.__serial.write(b"AT\r\n")
            response = self.read_rsp(size=6)
            if debug: print('{}'.format(response))
        if b'OK' in response:
            self.__serial.read()
            cmd = "AT+IPR=%d\n"%baudrate
            if debug: print('Setting baudrate to {}'.format(baudrate))
            self.__serial.write(cmd.encode())
            response = self.read_rsp(size=6)
            if debug: print('{}'.format(response))
            if b'OK' in response:
                if atneg_only:
                    return True
                if 'FiPy' in self.__sysname or 'GPy' in self.__sysname:
                    self.__serial = UART(1, baudrate=baudrate, pins=self.__pins, timeout_chars=100)
                else:
                    self.__serial = None
                    self.__serial = serial.Serial(port, baudrate, bytesize=serial.EIGHTBITS, timeout=0.1)
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
                print('ERROR in AT+IPR={} returned {}'.format(baudrate, response))
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
        from network import LTE
        LTE.modem_upgrade_mode()

    def upgrade_sd(self, ffile, mfile=None, baudrate=921600, retry=False, resume=False, debug=False, pkgdebug=False):
        print('<<< Welcome to the SQN3330 firmware updater >>>')
        success = True
        if not retry and mfile is not None:
            success = False
            success = self.__run(bootrom=True, resume=resume, switch_ffh=True, direct=False, debug=debug, pkgdebug=pkgdebug)
            time.sleep(1)
        if debug: print('Success1? {}'.format(success))
        if success:
            if mfile is not None:
                success = False
                success = self.__run(file_path=mfile, load_ffh=True, direct=False, baudrate=baudrate, debug=debug, pkgdebug=pkgdebug)
                time.sleep(1)
            else:
                success = True
        else:
            print('Unable to upgrade bootrom.')
        if debug: print('Success2? {}'.format(success))
        if success:
            self.__run(file_path=ffile, resume=True if mfile is not None else resume, baudrate=baudrate, direct=False, debug=debug, pkgdebug=pkgdebug)
        else:
            print('Unable to load updater from {}'.format(mfile))

    def upgrade_uart(self, ffh_mode=False, mfile=None, retry=False, resume=False, color=0x050505, debug=False, pkgdebug=False):
        success = True
        print('Preparing modem for upgrade...')
        if not retry and ffh_mode:
            success = False
            success = self.__run(bootrom=True, resume=resume, switch_ffh=True, direct=False, debug=debug, pkgdebug=pkgdebug)
            time.sleep(1)
        if success:
            if mfile is not None:
                success = False
                success = self.__run(file_path=mfile, load_ffh=True, direct=False, debug=debug, pkgdebug=pkgdebug)
                if debug: print('Success2? {}'.format(success))
                if success:
                    self.__run(mirror=True, load_ffh=False, direct=False, rgbled=color, debug=debug)
                else:
                    print('Unable to load updater from {}'.format(mfile))
            else:
                self.__run(mirror=True, load_ffh=ffh_mode, direct=False, rgbled=color, debug=debug)
        else:
            print('Unable to upgrade bootrom.')

    def show_version(self, port=None, debug=False):
        self.__run(port=port, debug=debug, version_only=True)

    def upgrade_ext(self, port, ffile, mfile, resume=False, debug=False, pkgdebug=False):
        success = True
        print('<<< Welcome to the SQN3330 firmware updater >>>')
        if mfile is not None:
            success = False
            success = self.__run(file_path=mfile, load_ffh=True, port=port, debug=debug, pkgdebug=pkgdebug)
        if success:
            self.__run(file_path=ffile, resume=True if mfile is not None else resume, direct=False, port=port, debug=debug, pkgdebug=pkgdebug)
        else:
            print('Unable to load updater from {}'.format(mfile))


if 'FiPy' in sysname or 'GPy' in sysname:
    def run(ffile, mfile=None, baudrate=921600, retry=False, resume=False, debug=False):
        fretry = False
        fresume = False
        sqnup = sqnsupgrade()
        if sqnup.check_files(ffile, mfile, debug):
            state = sqnup.detect_modem_state(initial_delay = 10)
            if debug: print('Modem state: {}'.format(state))
            if (not retry) and (not resume):
                if state == 0:
                    fretry = True
                    if mfile is None:
                        print('Your modem is in recovery mode. Please specify updater.elf file')
                        sys.exit(1)
                elif state == 4:
                    fresume = True
                elif state == -1:
                    print('Cannot detect modem state...Resuming regardless')
                    promt = input("please Enter 0 to Retry or 1 to Resume operation\n")
                    if promt:
                        fresume = True
                    else:
                        fretry = True
                if debug: print('Resume: {} Retry: {}'.format(fresume, fretry))
            else:
                fretry = retry
                fresume = resume

            sqnup.upgrade_sd(ffile, mfile, baudrate, fretry, fresume, debug, False)

    def uart(ffh_mode=False, mfile=None, retry=False, resume=False, color=0x050505, debug=False):
        fretry = False
        fresume = False
        sqnup = sqnsupgrade()
        state = sqnup.detect_modem_state(initial_delay = 10)
        if (not retry) and (not resume):
            if state == 0:
                print('Your modem is in recovery mode. You will need to use updater.elf file to upgrade.')
                fretry = True
            elif state == 4:
                fresume = True
            elif state == -1:
                print('Cannot detect modem state...Resuming regardless')
                promt = input("please Enter 0 to Retry or 1 to Resume operation\n")
                if promt:
                    fresume = True
                else:
                    fretry = True
            if debug: print('Resume: {} Retry: {}'.format(fresume, fretry))
        else:
            fretry = retry
            fresume = resume

        sqnup.upgrade_uart(ffh_mode, mfile, fretry, fresume, color, debug, False)

    def version(debug=False):
        sqnup = sqnsupgrade()
        sqnup.show_version(None, debug)

else:
    def run(port, ffile, mfile=None, resume=False, debug=False):
        sqnup = sqnsupgrade()
        if sqnup.check_files(ffile, mfile, debug):
            sqnup.upgrade_ext(port, ffile, mfile, resume, debug, False)

    def version(port, debug=False):
        sqnup = sqnsupgrade()
        sqnup.show_version(port, debug)
