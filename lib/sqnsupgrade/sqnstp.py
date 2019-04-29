#!/usr/bin/env python
#################################################################
#
#  Copyright (c) 2011 SEQUANS Communications.
#  All rights reserved.
#
#  This is confidential and proprietary source code of SEQUANS
#  Communications. The use of the present source code and all
#  its derived forms is exclusively governed by the restricted
#  terms and conditions set forth in the SEQUANS
#  Communications' EARLY ADOPTER AGREEMENT and/or LICENCE
#  AGREEMENT. The present source code and all its derived
#  forms can ONLY and EXCLUSIVELY be used with SEQUANS
#  Communications' products. The distribution/sale of the
#  present source code and all its derived forms is EXCLUSIVELY
#  RESERVED to regular LICENCE holder and otherwise STRICTLY
#  PROHIBITED.
#
#################################################################
import struct
import time
import os

try:
    sysname = os.uname().sysname
except:
    sysname = 'Windows'

# CRC-16(CCIT)
def crc16(s):
    crc = 0x0000
    table = [0x0000, 0x1021, 0x2042, 0x3063, 0x4084, 0x50a5, 0x60c6, 0x70e7,
        0x8108, 0x9129, 0xa14a, 0xb16b, 0xc18c, 0xd1ad, 0xe1ce, 0xf1ef,
        0x1231, 0x0210, 0x3273, 0x2252, 0x52b5, 0x4294, 0x72f7, 0x62d6,
        0x9339, 0x8318, 0xb37b, 0xa35a, 0xd3bd, 0xc39c, 0xf3ff, 0xe3de,
        0x2462, 0x3443, 0x0420, 0x1401, 0x64e6, 0x74c7, 0x44a4, 0x5485,
        0xa56a, 0xb54b, 0x8528, 0x9509, 0xe5ee, 0xf5cf, 0xc5ac, 0xd58d,
        0x3653, 0x2672, 0x1611, 0x0630, 0x76d7, 0x66f6, 0x5695, 0x46b4,
        0xb75b, 0xa77a, 0x9719, 0x8738, 0xf7df, 0xe7fe, 0xd79d, 0xc7bc,
        0x48c4, 0x58e5, 0x6886, 0x78a7, 0x0840, 0x1861, 0x2802, 0x3823,
        0xc9cc, 0xd9ed, 0xe98e, 0xf9af, 0x8948, 0x9969, 0xa90a, 0xb92b,
        0x5af5, 0x4ad4, 0x7ab7, 0x6a96, 0x1a71, 0x0a50, 0x3a33, 0x2a12,
        0xdbfd, 0xcbdc, 0xfbbf, 0xeb9e, 0x9b79, 0x8b58, 0xbb3b, 0xab1a,
        0x6ca6, 0x7c87, 0x4ce4, 0x5cc5, 0x2c22, 0x3c03, 0x0c60, 0x1c41,
        0xedae, 0xfd8f, 0xcdec, 0xddcd, 0xad2a, 0xbd0b, 0x8d68, 0x9d49,
        0x7e97, 0x6eb6, 0x5ed5, 0x4ef4, 0x3e13, 0x2e32, 0x1e51, 0x0e70,
        0xff9f, 0xefbe, 0xdfdd, 0xcffc, 0xbf1b, 0xaf3a, 0x9f59, 0x8f78,
        0x9188, 0x81a9, 0xb1ca, 0xa1eb, 0xd10c, 0xc12d, 0xf14e, 0xe16f,
        0x1080, 0x00a1, 0x30c2, 0x20e3, 0x5004, 0x4025, 0x7046, 0x6067,
        0x83b9, 0x9398, 0xa3fb, 0xb3da, 0xc33d, 0xd31c, 0xe37f, 0xf35e,
        0x02b1, 0x1290, 0x22f3, 0x32d2, 0x4235, 0x5214, 0x6277, 0x7256,
        0xb5ea, 0xa5cb, 0x95a8, 0x8589, 0xf56e, 0xe54f, 0xd52c, 0xc50d,
        0x34e2, 0x24c3, 0x14a0, 0x0481, 0x7466, 0x6447, 0x5424, 0x4405,
        0xa7db, 0xb7fa, 0x8799, 0x97b8, 0xe75f, 0xf77e, 0xc71d, 0xd73c,
        0x26d3, 0x36f2, 0x0691, 0x16b0, 0x6657, 0x7676, 0x4615, 0x5634,
        0xd94c, 0xc96d, 0xf90e, 0xe92f, 0x99c8, 0x89e9, 0xb98a, 0xa9ab,
        0x5844, 0x4865, 0x7806, 0x6827, 0x18c0, 0x08e1, 0x3882, 0x28a3,
        0xcb7d, 0xdb5c, 0xeb3f, 0xfb1e, 0x8bf9, 0x9bd8, 0xabbb, 0xbb9a,
        0x4a75, 0x5a54, 0x6a37, 0x7a16, 0x0af1, 0x1ad0, 0x2ab3, 0x3a92,
        0xfd2e, 0xed0f, 0xdd6c, 0xcd4d, 0xbdaa, 0xad8b, 0x9de8, 0x8dc9,
        0x7c26, 0x6c07, 0x5c64, 0x4c45, 0x3ca2, 0x2c83, 0x1ce0, 0x0cc1,
        0xef1f, 0xff3e, 0xcf5d, 0xdf7c, 0xaf9b, 0xbfba, 0x8fd9, 0x9ff8,
        0x6e17, 0x7e36, 0x4e55, 0x5e74, 0x2e93, 0x3eb2, 0x0ed1, 0x1ef0]
    for ch in s:
        crc = ((crc<<8)&0xff00) ^ table[((crc>>8)&0xff)^ch]
    return crc

def usleep(x):
    time.sleep(x/1000000.0)

def hexdump(src, length=32):
    if len(src) == 0:
        return
    src = src[:length]
    FILTER = ''.join([(len(repr(chr(x))) == 3) and chr(x) or '.' for x in range(256)])
    lines = []
    for c in range(0, len(src), length):
        chars = src[c:c+length]
    hex = ' '.join(["%02x" % ord(x) for x in chars])
    printable = ''.join(["%s" % ((ord(x) <= 127 and FILTER[ord(x)]) or '.') for x in chars])
    lines.append("%04x %-*s %s\n" % (c, length*3, hex, printable))
    print(''.join(lines))


class MException(BaseException):
    def __init__(self, s):
        self.s = s
    def __str__(self):
        return self.s

class SerialDev(object):
    def __init__(self, serial, baud, timeout=90000):    # 90 seconds timeout
        self.serial = serial
        self.timeout = timeout

    def read(self, n):
        global sysname
        _n = n
        t = self.timeout
        r = b''
        while t > 0:
            c = self.serial.read(_n)
            if c:
                r += c
                if len(r) == n:
                    break
                _n -= len(c)
            if 'FiPy' in sysname or 'GPy' in sysname:
                time.sleep_ms(2)
            else:
                time.sleep(0.002)
            t -= 2
        return r

    def write(self, s):
        self.serial.write(s)

    def devastate(self):
        self.serial.read()

    def close(self):
        self.serial.close()

    def set_timeout(self, timeout):
        self.timeout = timeout * 1000


class Master:
    RESET               = 0
    SESSION_OPEN        = 1
    TRANSFER_BLOCK_CMD  = 2
    TRANSFER_BLOCK      = 3

    MREQH = b">IBBHIHH"
    SRSPH = b">IBBHIHH"
    SRSP_SESSION_OPEN = b">BBH"
    SRSP_TRANSFER_BLOCK = b">H"

    MREQH_SIZE = struct.calcsize(MREQH)
    SRSPH_SIZE = struct.calcsize(SRSPH)
    SRSP_SESSION_OPEN_SIZE = struct.calcsize(SRSP_SESSION_OPEN)
    SRSP_TRANSFER_BLOCK_SIZE = struct.calcsize(SRSP_TRANSFER_BLOCK)

    MREQ_SIGNATURE = 0x66617374
    SRSP_SIGNATURE = 0x74736166

    def __init__(self, dev, debug=False, pkgdebug=False):
        self.sid = 0
        self.tid = 0
        self.dev = dev
        self.debug = debug
        self.pkgdebug = pkgdebug
        self.mreq = []
        self.srsp = []
        self.version = 1
        self.max_transfer = 16

    @staticmethod
    def mreq_ack(op):
        return op | 0x80

    def wipe(self):
        self.dev.devastate()

    def read(self, n):
        r = self.dev.read(n)
        if self.pkgdebug:
            print("IN")
            hexdump(r)
        return r


    def write(self, s):
        self.dev.write(s)
        if self.pkgdebug:
            print("OUT")
            # hexdump(s.decode('ascii'))


    def make_mreq(self, op, pld):
        assert self.MREQH_SIZE + len(pld) <= self.max_transfer

        if len(pld) != 0:
            pcrc = crc16(pld)
        else:
            pcrc = 0
        hcrc = crc16(struct.pack(self.MREQH,
                           self.MREQ_SIGNATURE,
                           op, self.sid, len(pld),
                           self.tid,
                           0, pcrc))
        return struct.pack(self.MREQH,
                           self.MREQ_SIGNATURE,
                           op, self.sid, len(pld),
                           self.tid,
                           hcrc, pcrc)


    def decode_srsp(self, p, show=False):
        if len(p) < self.SRSPH_SIZE:
            raise MException("SRSP header too small: %d" % len(p))

        (magic, op, sid, plen, tid, hcrc, pcrc) = struct.unpack(self.SRSPH, p[:self.SRSPH_SIZE])
        if show and self.debug:
            print('magic=0x%08X, op=0x%X, sid=0x%X, plen=0x%X, tid=0x%X, hcrc=0x%X, pcrc=0x%X' % (magic, op, sid, plen, tid, hcrc, pcrc))

        if magic != self.SRSP_SIGNATURE:
            print("Wrong SRSP signature: 0x%08X" % magic)
            #raise MException("Wrong SRSP signature: 0x%08X" % magic)
        elif show and self.debug:
            print("Correct SRSP signature: 0x%08X" % magic)

        if hcrc != 0:
            chcrc = crc16(struct.pack(self.SRSPH, self.SRSP_SIGNATURE, op, sid, plen, tid, 0, pcrc))
            if hcrc != chcrc:
                raise MException("Wrong header CRC: 0x%04X" % hcrc)

        return dict(op=op, sid=sid, tid=tid, plen=plen, pcrc=pcrc)


    def verify_srsp_data(self, p, plen, pcrc):
        if len(p) != plen:
            raise MException("Wrong payload size: %d" % plen)
        if plen != 0 and pcrc != 0 and pcrc != crc16(p):
            raise MException("Wrong payload CRC: 0x%04X" % pcrc)


    def verify_session(self, i, op):
        if i['op'] != Master.mreq_ack(op):
            raise MException("Invalid op: 0x%02x" % i['op'])
        if i['sid'] != self.sid:
            raise MException("Invalid sid: %d" % i['sid'])
        if i['tid'] != self.tid:
            raise MException("Invalid sid: %d" % i['tid'])


    def decode_open_session(self, p):
        if len(p) < self.SRSP_SESSION_OPEN_SIZE:
            raise MException("OpenSession data too small: %d" % len(p))
        (ok, ver, mts) = struct.unpack(self.SRSP_SESSION_OPEN, p[:self.SRSP_SESSION_OPEN_SIZE])
        if not ok:
            raise MException("OpenSession: failed to open")

        self.version = ver
        self.max_transfer = mts
        print("Session opened: version %d, max transfer %s bytes" % (ver, mts))


    def reset(self, closing=False):
        self.write(self.make_mreq(self.RESET, []))
        r = self.read(self.SRSPH_SIZE)
        if closing:
            return
        i = self.decode_srsp(r, show=True)
        if i['op'] != Master.mreq_ack(self.RESET):
            raise MException("Reset: invalid op: 0x%02x" % i['op'])

        self.sid = 0
        self.tid = 0


    def open_session(self):
        self.sid = 1
        self.tid = 1
        self.write(self.make_mreq(self.SESSION_OPEN, []))
        r = self.read(self.SRSPH_SIZE)
        i = self.decode_srsp(r)
        self.verify_session(i, self.SESSION_OPEN)
        r = self.read(self.SRSP_SESSION_OPEN_SIZE)
        self.verify_srsp_data(r, i['plen'], i['pcrc'])
        self.decode_open_session(r)
        self.tid += 1


    def send_data(self, blobfile, filesize, trials=4, bootrom=None):
        global sysname

        class Trial:
            def __init__(self, trials):
                self.trials = trials
            def need_retry(self, c, *a, **k):
                try:
                    c(*a, **k)
                except MException:
                    self.trials -= 1
                    if self.trials > 0: return True
                    else: raise
                return False

        trial = Trial(trials)

        downloaded = 0

        while True:
            # if 'FiPy' in sysname or 'GPy' in sysname:
            #     data = blobfile.read(1536)
            # else:
            #     #data = blobfile.read(512)
            #     data = blobfile.read(768)
            data = blobfile.read(2048)
            size = len(data)
            if size:
                while size:
                    l = min(size, self.max_transfer-self.MREQH_SIZE)
                    l = min(l, 2048 - 32) # 31x0 mii limitation

                    trials = 4
                    while True:
                        pld = struct.pack(">H", l)
                        self.write(self.make_mreq(self.TRANSFER_BLOCK_CMD, pld))
                        self.write(pld)
                        try:
                            r = self.read(self.SRSPH_SIZE)
                            i = self.decode_srsp(r)
                        except MException:
                            trials -= 1
                            if not trials: raise
                            continue
                        break

                    if trial.need_retry(self.verify_session, i, self.TRANSFER_BLOCK_CMD): continue
                    self.tid += 1

                    trials = 4
                    while True:
                        pld = data[:l]
                        self.write(self.make_mreq(self.TRANSFER_BLOCK, pld))
                        self.write(pld)
                        try:
                            r = self.read(self.SRSPH_SIZE)
                            i = self.decode_srsp(r)
                        except MException:
                            trials -= 1
                            if not trials: raise
                            continue
                        if trial.need_retry(self.verify_session, i, self.TRANSFER_BLOCK): continue
                        r = self.read(self.SRSP_TRANSFER_BLOCK_SIZE)
                        break
                    if trial.need_retry(self.verify_srsp_data, r, i['plen'], i['pcrc']): continue
                    self.tid += 1

                    (residue, ) = struct.unpack(">H", r)
                    if residue > 0:
                        print("Slave didn't consume %d bytes" % residue)
                        l -= residue

                    data = data[l:]
                    size -= l
                    downloaded += l
                self.progress("Sending %d bytes" % filesize, downloaded, filesize)
            else:
                break

        blobfile.close()
        self.progressComplete()

        return True


    def progress(self, what, downloaded, total, barLen=40):
        percent = float(downloaded)/total
        hashes = '#' * int(round(percent*barLen))
        spaces = ' ' * (barLen - len(hashes))
        if 'FiPy' in sysname or 'GPy' in sysname:
            print('\r%s: [%s%s] %3d%%' % (what, hashes, spaces, int(round(percent*100))), end='')
        else:
            print('\r%s: [%s%s] %3d%%' % (what, hashes, spaces, int(round(percent*100))), end='', flush=True)


    def progressComplete(self):
        print()


class args(object):
    pass

def start(elf, elfsize, serial, baud=3686400, retry=None, debug=None, AT=True, pkgdebug=False):
    dev = None

    try:
        # The base-two logarithm of the window size, which therefore ranges between 512 and 32768
        # 12 is 4096K
        wbits = 12
        dev = SerialDev(serial, baud)
        push = lambda m: m.send_data(elf, elfsize)
    except:
        raise

    time.sleep(0.05)
    m = Master(dev, debug=debug, pkgdebug=pkgdebug)

    while True:
        try:
            if debug: print('running m.wipe')
            m.wipe()
            if debug: print('running m.reset')
            m.reset()
            if debug: print('running m.open_session')
            m.open_session()
            if debug: print('running push(m)')
            push(m)
            if debug: print('running dev.set_timeout(2)')
            dev.set_timeout(2)
            if debug: print('running m.reset(True)')
            m.reset(True)
            return True
        except MException as ex:
            print(str(ex))
            if retry:
                continue
            else:
                return False
        break
        return False
