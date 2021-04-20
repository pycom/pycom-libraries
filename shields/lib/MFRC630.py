'''
Pyscan NFC library
Copyright (c) 2019, Pycom Limited.

Based on a library for NXP's MFRC630 NFC IC https://github.com/iwanders/MFRC630

The MIT License (MIT)

Copyright (c) 2016 Ivor Wanders

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

'''

import time, binascii

class MFRC630:

    NFC_I2CADDR = const(0x28)
    # commands
    MFRC630_CMD_IDLE = const(0x00)  # (no arguments) ; no action, cancels current command execution. */
    MFRC630_CMD_LPCD = const(0x01)  # (no arguments) ; low-power card detection. */
    MFRC630_CMD_LOADKEY = const(0x02)  # (keybyte1), (keybyte2), (keybyte3), (keybyte4), (keybyte5),
    MFRC630_CMD_MFAUTHENT = const(0x03)  # 60h or 61h, (block address), (card serial number byte0), (card
    MFRC630_CMD_RECEIVE = const(0x05)  # (no arguments) ; activates the receive circuit. */
    MFRC630_CMD_TRANSMIT = const(0x06)  # bytes to send: byte1, byte2, ...;  transmits data from the FIFO
    MFRC630_CMD_TRANSCEIVE = const(0x07)  # bytes to send: byte1, byte2, ....;  transmits data from the FIFO
    MFRC630_CMD_WRITEE2 = const(0x08)  # addressH, addressL, data; gets one byte from FIFO buffer and
    MFRC630_CMD_WRITEE2PAGE = const(0x09)  # (page Address), data0, [data1..data63]; gets up to 64 bytes (one
    MFRC630_CMD_READE2 = const(0x0A)  # addressH, address L, length; reads data from the EEPROM and copies
    MFRC630_CMD_LOADREG = const(0x0C)  # (EEPROM addressH), (EEPROM addressL), RegAdr, (number of Register
    MFRC630_CMD_LOADPROTOCOL = const(0x0D)  # (Protocol number RX), (Protocol number TX) reads data from the
    MFRC630_CMD_LOADKEYE2 = const(0x0E)  # KeyNr; copies a key from the EEPROM into the key buffer. */
    MFRC630_CMD_STOREKEYE2 = const(0x0F)  # KeyNr, byte1, byte2, byte3, byte4, byte5, byte6; stores a MIFARE
    MFRC630_CMD_READRNR = const(0x1C)  # (no arguments) ; Copies bytes from the Random Number generator
    MFRC630_CMD_SOFTRESET = const(0x1F)  # (no arguments) ; resets the MFRC630. */

    MFRC630_STATUS_STATE_IDLE = const(0b000)  # Status register; Idle
    MFRC630_STATUS_STATE_TXWAIT = const(0b001)  # Status register; Tx wait
    MFRC630_STATUS_STATE_TRANSMITTING = const(0b011)  # Status register; Transmitting.
    MFRC630_STATUS_STATE_RXWAIT = const(0b101)  # Status register; Rx wait.
    MFRC630_STATUS_STATE_WAIT_FOR_DATA = const(0b110)  # Status register; Waiting for data.
    MFRC630_STATUS_STATE_RECEIVING = const(0b111)  # Status register; Receiving data.
    MFRC630_STATUS_STATE_NOT_USED = const(0b100)  # Status register; Not used.
    MFRC630_STATUS_CRYPTO1_ON = const(1 << 5)  # Status register; Crypto1 (MIFARE authentication) is on.

    MFRC630_PROTO_ISO14443A_106_MILLER_MANCHESTER = const(0)
    MFRC630_PROTO_ISO14443A_212_MILLER_BPSK = const(1)
    MFRC630_PROTO_ISO14443A_424_MILLER_BPSK = const(2)
    MFRC630_PROTO_ISO14443A_848_MILLER_BPSK = const(3)
    MFRC630_PROTO_ISO14443B_106_NRZ_BPSK = const(4)
    MFRC630_PROTO_ISO14443B_212_NRZ_BPSK = const(5)
    MFRC630_PROTO_ISO14443B_424_NRZ_BPSK = const(6)
    MFRC630_PROTO_ISO14443B_848_NRZ_BPSK = const(7)
    MFRC630_PROTO_FELICA_212_MANCHESTER_MANCHESTER = const(8)
    MFRC630_PROTO_FELICA_424_MANCHESTER_MANCHESTER = const(9)
    MFRC630_PROTO_ISO15693_1_OF_4_SSC = const(10)
    MFRC630_PROTO_ISO15693_1_OF_4_DSC = const(11)
    MFRC630_PROTO_ISO15693_1_OF_256_SSC = const(12)
    MFRC630_PROTO_EPC_UID_UNITRAY_SSC = const(13)
    MFRC630_PROTO_ISO18000_MODE_3 = const(14)
    MFRC630_RECOM_14443A_ID1_106 = [ 0x8A, 0x08, 0x21, 0x1A, 0x18, 0x18, 0x0F, 0x27, 0x00, 0xC0, 0x12, 0xCF, 0x00, 0x04, 0x90, 0x32, 0x12, 0x0A ]
    MFRC630_RECOM_14443A_ID1_212 = [ 0x8E, 0x12, 0x11, 0x06, 0x18, 0x18, 0x0F, 0x10, 0x00, 0xC0, 0x12, 0xCF, 0x00, 0x05, 0x90, 0x3F, 0x12, 0x02 ]
    MFRC630_RECOM_14443A_ID1_424 = [ 0x8E, 0x12, 0x11, 0x06, 0x18, 0x18, 0x0F, 0x08, 0x00, 0xC0, 0x12, 0xCF, 0x00, 0x06, 0x90, 0x3F, 0x12, 0x0A ]
    MFRC630_RECOM_14443A_ID1_848 = [ 0x8F, 0xDB, 0x11, 0x06, 0x18, 0x18, 0x0F, 0x02, 0x00, 0xC0, 0x12, 0xCF, 0x00, 0x07, 0x90, 0x3F, 0x12, 0x02 ]
    MFRC630_ISO14443_CMD_REQA = const(0x26)  # request (idle -> ready)
    MFRC630_ISO14443_CMD_WUPA = const(0x52)  # wake up type a (idle / halt -> ready)
    MFRC630_ISO14443_CAS_LEVEL_1 = const(0x93)  # Cascade level 1 for select.
    MFRC630_ISO14443_CAS_LEVEL_2 = const(0x95)  # Cascade level 2 for select.
    MFRC630_ISO14443_CAS_LEVEL_3 = const(0x97)  # Cascade level 3 for select.
    MFRC630_MF_AUTH_KEY_A = const(0x60)  # A key_type for mifare auth.
    MFRC630_MF_AUTH_KEY_B = const(0x61)  # A key_type for mifare auth.
    MFRC630_MF_CMD_READ = const(0x30)  # To read a block from mifare card.
    MFRC630_MF_CMD_WRITE = const(0xA0)  # To write a block to a mifare card.
    MFRC630_MF_ACK = const(0x0A)  # Sent by cards to acknowledge an operation.

    # registers
    MFRC630_REG_COMMAND = const(0x00)  # Starts and stops command execution
    MFRC630_REG_HOSTCTRL = const(0x01)  # Host control register
    MFRC630_REG_FIFOCONTROL = const(0x02)  # Control register of the FIFO
    MFRC630_REG_WATERLEVEL = const(0x03)  # Level of the FIFO underflow and overflow warning
    MFRC630_REG_FIFOLENGTH = const(0x04)  # Length of the FIFO
    MFRC630_REG_FIFODATA = const(0x05)  # Data In/Out exchange register of FIFO buffer
    MFRC630_REG_IRQ0 = const(0x06)  # Interrupt register 0
    MFRC630_REG_IRQ1 = const(0x07)  # Interrupt register 1
    MFRC630_REG_IRQ0EN = const(0x08)  # Interrupt enable register 0
    MFRC630_REG_IRQ1EN = const(0x09)  # Interrupt enable register 1
    MFRC630_REG_ERROR = const(0x0A)  # Error bits showing the error status of the last command execution
    MFRC630_REG_STATUS = const(0x0B)  # Contains status of the communication
    MFRC630_REG_RXBITCTRL = const(0x0C)  # Control for anticoll. adjustments for bit oriented protocols
    MFRC630_REG_RXCOLL = const(0x0D)  # Collision position register
    MFRC630_REG_TCONTROL = const(0x0E)  # Control of Timer 0..3
    MFRC630_REG_T0CONTROL = const(0x0F)  # Control of Timer0
    MFRC630_REG_T0RELOADHI = const(0x10)  # High register of the reload value of Timer0
    MFRC630_REG_T0RELOADLO = const(0x11)  # Low register of the reload value of Timer0
    MFRC630_REG_T0COUNTERVALHI = const(0x12)  # Counter value high register of Timer0
    MFRC630_REG_T0COUNTERVALLO = const(0x13)  # Counter value low register of Timer0
    MFRC630_REG_T1CONTROL = const(0x14)  # Control of Timer1
    MFRC630_REG_T1RELOADHI = const(0x15)  # High register of the reload value of Timer1
    MFRC630_REG_T1COUNTERVALHI = const(0x17)  # Counter value high register of Timer1
    MFRC630_REG_T1COUNTERVALLO = const(0x18)  # Counter value low register of Timer1
    MFRC630_REG_T2CONTROL = const(0x19)  # Control of Timer2
    MFRC630_REG_T2RELOADHI = const(0x1A)  # High byte of the reload value of Timer2
    MFRC630_REG_T2RELOADLO = const(0x1B)  # Low byte of the reload value of Timer2
    MFRC630_REG_T2COUNTERVALHI = const(0x1C)  # Counter value high byte of Timer2
    MFRC630_REG_T2COUNTERVALLO = const(0x1D)  # Counter value low byte of Timer2
    MFRC630_REG_T3CONTROL = const(0x1E)  # Control of Timer3
    MFRC630_REG_T3RELOADHI = const(0x1F)  # High byte of the reload value of Timer3
    MFRC630_REG_T3RELOADLO = const(0x20)  # Low byte of the reload value of Timer3
    MFRC630_REG_T3COUNTERVALHI = const(0x21)  # Counter value high byte of Timer3
    MFRC630_REG_T3COUNTERVALLO = const(0x22) # Counter value low byte of Timer3
    MFRC630_REG_T4CONTROL = const(0x23)  # Control of Timer4
    MFRC630_REG_T4RELOADHI = const(0x24)  # High byte of the reload value of Timer4
    MFRC630_REG_T4RELOADLO = const(0x25)  # Low byte of the reload value of Timer4
    MFRC630_REG_T4COUNTERVALHI = const(0x26)  # Counter value high byte of Timer4
    MFRC630_REG_T4COUNTERVALLO = const(0x27)  # Counter value low byte of Timer4
    MFRC630_REG_DRVMOD = const(0x28)  # Driver mode register
    MFRC630_REG_TXAMP = const(0x29)  # Transmitter amplifier register
    MFRC630_REG_DRVCON = const(0x2A)  # Driver configuration register
    MFRC630_REG_TXL = const(0x2B)  # Transmitter register
    MFRC630_REG_TXCRCPRESET = const(0x2C)  # Transmitter CRC control register, preset value
    MFRC630_REG_RXCRCCON = const(0x2D)  # Receiver CRC control register, preset value
    MFRC630_REG_TXDATANUM = const(0x2E)  # Transmitter data number register
    MFRC630_REG_TXMODWIDTH = const(0x2F)  # Transmitter modulation width register
    MFRC630_REG_TXSYM10BURSTLEN = const(0x30)  # Transmitter symbol 1 + symbol 0 burst length register
    MFRC630_REG_TXWAITCTRL = const(0x31) # Transmitter wait control
    MFRC630_REG_TXWAITLO = const(0x32)  # Transmitter wait low
    MFRC630_REG_FRAMECON = const(0x33)  # Transmitter frame control
    MFRC630_REG_RXSOFD = const(0x34)  # Receiver start of frame detection
    MFRC630_REG_RXCTRL = const(0x35)  # Receiver control register
    MFRC630_REG_RXWAIT = const(0x36)  # Receiver wait register
    MFRC630_REG_RXTHRESHOLD = const(0x37)  # Receiver threshold register
    MFRC630_REG_RCV = const(0x38)  # Receiver register
    MFRC630_REG_RXANA = const(0x39)  # Receiver analog register
    MFRC630_REG_RFU = const(0x3A)  # (Reserved for future use)
    MFRC630_REG_SERIALSPEED = const(0x3B)  # Serial speed register
    MFRC630_REG_LFO_TRIMM = const(0x3C)  # Low-power oscillator trimming register
    MFRC630_REG_PLL_CTRL = const(0x3D)  # IntegerN PLL control register, for mcu clock output adjustment
    MFRC630_REG_PLL_DIVOUT = const(0x3E)  # IntegerN PLL control register, for mcu clock output adjustment
    MFRC630_REG_LPCD_QMIN = const(0x3F)  # Low-power card detection Q channel minimum threshold
    MFRC630_REG_LPCD_QMAX = const(0x40)  # Low-power card detection Q channel maximum threshold
    MFRC630_REG_LPCD_IMIN = const(0x41)  # Low-power card detection I channel minimum threshold
    MFRC630_REG_LPCD_I_RESULT = const(0x42)  # Low-power card detection I channel result register
    MFRC630_REG_LPCD_Q_RESULT = const(0x43)  # Low-power card detection Q channel result register
    MFRC630_REG_PADEN = const(0x44)  # PIN enable register
    MFRC630_REG_PADOUT = const(0x45)  # PIN out register
    MFRC630_REG_PADIN = const(0x46)  # PIN in register
    MFRC630_REG_SIGOUT = const(0x47)  # Enables and controls the SIGOUT Pin
    MFRC630_REG_VERSION = const(0x7F)  # Version and subversion register

    MFRC630_TXDATANUM_DATAEN = const(1 << 3)
    MFRC630_RECOM_14443A_CRC = const(0x18)

    MFRC630_ERROR_EE_ERR = const(1 << 7)
    MFRC630_ERROR_FIFOWRERR = const(1 << 6)
    MFRC630_ERROR_FIFOOVL = const(1 << 5)
    MFRC630_ERROR_MINFRAMEERR = const(1 << 4)
    MFRC630_ERROR_NODATAERR = const(1 << 3)
    MFRC630_ERROR_COLLDET = const(1 << 2)
    MFRC630_ERROR_PROTERR = const(1 << 1)
    MFRC630_ERROR_INTEGERR = const(1 << 0)

    MFRC630_CRC_ON = const(1)
    MFRC630_CRC_OFF = const(0)

    MFRC630_IRQ0EN_IRQ_INV = const(1 << 7)
    MFRC630_IRQ0EN_HIALERT_IRQEN = const(1 << 6)
    MFRC630_IRQ0EN_LOALERT_IRQEN = const(1 << 5)
    MFRC630_IRQ0EN_IDLE_IRQEN = const(1 << 4)
    MFRC630_IRQ0EN_TX_IRQEN = const(1 << 3)
    MFRC630_IRQ0EN_RX_IRQEN = const(1 << 2)
    MFRC630_IRQ0EN_ERR_IRQEN = const(1 << 1)
    MFRC630_IRQ0EN_RXSOF_IRQEN = const(1 << 0)

    MFRC630_IRQ1EN_TIMER0_IRQEN = const(1 << 0)

    MFRC630_TCONTROL_CLK_211KHZ = const(0b01)
    MFRC630_TCONTROL_START_TX_END = const(0b01 << 4)

    MFRC630_IRQ1_GLOBAL_IRQ = const(1 << 6)

    MFRC630_IRQ0_ERR_IRQ = const(1 << 1)
    MFRC630_IRQ0_RX_IRQ = const(1 << 2)

    def __init__(self, pyscan=None, sda='P22', scl='P21', timeout=None, debug=False):
        if pyscan is not None:
            self.i2c = pyscan.i2c
        else:
            from machine import I2C
            self.i2c = I2C(0, mode=I2C.MASTER, pins=(sda, scl))
        self._DEBUG = debug
        self.mfrc630_cmd_reset()

        # ToDo: Timeout not yet implemented!
        # self.chrono = Timer.Chrono()
        # self.timeout = timeout
        # self.timeout_status = True

    def print_debug(self, msg):
        if self._DEBUG:
            print(msg)

    def mfrc630_read_reg(self, reg):
        return self.i2c.readfrom_mem(NFC_I2CADDR, reg, 1)[0]

    def mfrc630_write_reg(self, reg, data):
        self.i2c.writeto_mem(NFC_I2CADDR, reg, bytes([data & 0xFF]))

    def mfrc630_write_regs(self, reg, data):
        self.i2c.writeto_mem(NFC_I2CADDR, reg, bytes(data))

    def mfrc630_read_fifo(self, len):
        if len > 0:
            return self.i2c.readfrom_mem(NFC_I2CADDR, MFRC630_REG_FIFODATA, len)
        else:
            return None

    def mfrc630_cmd_idle(self):
        self.mfrc630_write_reg(MFRC630_REG_COMMAND, MFRC630_CMD_IDLE)

    def mfrc630_flush_fifo(self):
        self.mfrc630_write_reg(MFRC630_REG_FIFOCONTROL, 1 << 4)

    def mfrc630_setup_fifo(self):
        self.mfrc630_write_reg(MFRC630_REG_FIFOCONTROL, 0x90)
        self.mfrc630_write_reg(MFRC630_REG_WATERLEVEL, 0xFE)

    def mfrc630_write_fifo(self, data):
        self.mfrc630_write_regs(MFRC630_REG_FIFODATA, data)

    def mfrc630_cmd_load_protocol(self, rx, tx):
        self.mfrc630_flush_fifo()
        self.mfrc630_write_fifo([rx, tx])
        self.mfrc630_write_reg(MFRC630_REG_COMMAND, MFRC630_CMD_LOADPROTOCOL)

    def mfrc630_cmd_transceive(self, data):
        self.mfrc630_cmd_idle()
        self.mfrc630_flush_fifo()
        self.mfrc630_setup_fifo()
        self.mfrc630_write_fifo(data)
        self.mfrc630_write_reg(MFRC630_REG_COMMAND, MFRC630_CMD_TRANSCEIVE)

    def mfrc630_cmd_init(self):
        self.mfrc630_write_regs(MFRC630_REG_DRVMOD, self.MFRC630_RECOM_14443A_ID1_106)
        self.mfrc630_write_reg(0x28, 0x8E)
        self.mfrc630_write_reg(0x29, 0x15)
        self.mfrc630_write_reg(0x2A, 0x11)
        self.mfrc630_write_reg(0x2B, 0x06)

    def mfrc630_cmd_reset(self):
        self.mfrc630_cmd_idle()
        self.mfrc630_write_reg(MFRC630_REG_COMMAND, MFRC630_CMD_SOFTRESET)

    def mfrc630_clear_irq0(self):
        self.mfrc630_write_reg(MFRC630_REG_IRQ0, ~(1 << 7))

    def mfrc630_clear_irq1(self):
        self.mfrc630_write_reg(MFRC630_REG_IRQ1, ~(1 << 7))

    def mfrc630_irq0(self):
        return self.mfrc630_read_reg(MFRC630_REG_IRQ0)

    def mfrc630_irq1(self):
        return self.mfrc630_read_reg(MFRC630_REG_IRQ1)

    def mfrc630_timer_set_control(self, timer, value):
        self.mfrc630_write_reg(MFRC630_REG_T0CONTROL + (5 * timer), value)

    def mfrc630_timer_set_reload(self, timer, value):
        self.mfrc630_write_reg(MFRC630_REG_T0RELOADHI + (5 * timer), value >> 8)
        self.mfrc630_write_reg(MFRC630_REG_T0RELOADLO + (5 * timer), 0xFF)

    def mfrc630_timer_set_value(self, timer, value):
        self.mfrc630_write_reg(MFRC630_REG_T0COUNTERVALHI + (5 * timer), value >> 8)
        self.mfrc630_write_reg(MFRC630_REG_T0COUNTERVALLO + (5 * timer), 0xFF)

    def mfrc630_fifo_length(self):
        # should do 512 byte fifo handling here
        return self.mfrc630_read_reg(MFRC630_REG_FIFOLENGTH)

    def mfrc630_status(self):
        return self.mfrc630_read_reg(MFRC630_REG_STATUS)

    def mfrc630_error(self):
        return self.mfrc630_read_reg(MFRC630_REG_ERROR)

    def mfrc630_cmd_load_key(self, key):
      self.mfrc630_cmd_idle()
      self.mfrc630_flush_fifo()
      self.mfrc630_write_fifo(key)
      self.mfrc630_write_reg(MFRC630_REG_COMMAND, MFRC630_CMD_LOADKEY)

    def mfrc630_cmd_auth(self, key_type, block_address, card_uid):
        self.mfrc630_cmd_idle()
        parameters = [ key_type, block_address, card_uid[0], card_uid[1], card_uid[2], card_uid[3] ]
        self.mfrc630_flush_fifo()
        self.mfrc630_write_fifo(parameters)
        self.mfrc630_write_reg(MFRC630_REG_COMMAND, MFRC630_CMD_MFAUTHENT)

    def mfrc630_MF_read_block(self, block_address, dest):
        self.mfrc630_flush_fifo()

        self.mfrc630_write_reg(MFRC630_REG_TXCRCPRESET, MFRC630_RECOM_14443A_CRC | MFRC630_CRC_ON)
        self.mfrc630_write_reg(MFRC630_REG_RXCRCCON, MFRC630_RECOM_14443A_CRC | MFRC630_CRC_ON)

        send_req = [ MFRC630_MF_CMD_READ, block_address ]

        # configure a timeout timer.
        timer_for_timeout = 0  # should match the enabled interupt.

        # enable the global IRQ for idle, errors and timer.
        self.mfrc630_write_reg(MFRC630_REG_IRQ0EN, MFRC630_IRQ0EN_IDLE_IRQEN | MFRC630_IRQ0EN_ERR_IRQEN)
        self.mfrc630_write_reg(MFRC630_REG_IRQ1EN, MFRC630_IRQ1EN_TIMER0_IRQEN)


        # Set timer to 221 kHz clock, start at the end of Tx.
        self.mfrc630_timer_set_control(timer_for_timeout, MFRC630_TCONTROL_CLK_211KHZ | MFRC630_TCONTROL_START_TX_END)
        # Frame waiting time: FWT = (256 x 16/fc) x 2 FWI
        # FWI defaults to four... so that would mean wait for a maximum of ~ 5ms
        self.mfrc630_timer_set_reload(timer_for_timeout, 2000)  # 2000 ticks of 5 usec is 10 ms.
        self.mfrc630_timer_set_value(timer_for_timeout, 2000)

        irq1_value = 0
        irq0_value = 0

        self.mfrc630_clear_irq0()  # clear irq0
        self.mfrc630_clear_irq1()  # clear irq1

        # Go into send, then straight after in receive.
        self.mfrc630_cmd_transceive(send_req)

        # block until we are done
        while not (irq1_value & (1 << timer_for_timeout)):
            irq1_value = self.mfrc630_irq1()
            if (irq1_value & MFRC630_IRQ1_GLOBAL_IRQ):
                self.print_debug("irq1: %x" % irq1_value)
                break  # stop polling irq1 and quit the timeout loop.

        self.mfrc630_cmd_idle()

        if irq1_value & (1 << timer_for_timeout):
            self.print_debug("this indicates a timeout")
            # this indicates a timeout
            return 0

        irq0_value = self.mfrc630_irq0()
        if (irq0_value & MFRC630_IRQ0_ERR_IRQ):
            self.print_debug("some error")
            # some error
            return 0

        self.print_debug("all seems to be well...")
        # all seems to be well...
        buffer_length = self.mfrc630_fifo_length()
        rx_len = buffer_length if (buffer_length <= 16) else 16
        dest = self.mfrc630_read_fifo(rx_len)
        return dest


    def mfrc630_iso14443a_WUPA_REQA(self, instruction):
        self.mfrc630_cmd_idle()

        self.mfrc630_flush_fifo()

        #Set register such that we sent 7 bits, set DataEn such that we can send data
        self.mfrc630_write_reg(MFRC630_REG_TXDATANUM, 7 | MFRC630_TXDATANUM_DATAEN)

        # disable the CRC registers
        self.mfrc630_write_reg(MFRC630_REG_TXCRCPRESET, MFRC630_RECOM_14443A_CRC | MFRC630_CRC_OFF)
        self.mfrc630_write_reg(MFRC630_REG_RXCRCCON, MFRC630_RECOM_14443A_CRC | MFRC630_CRC_OFF)
        self.mfrc630_write_reg(MFRC630_REG_RXBITCTRL, 0)

        # clear interrupts
        self.mfrc630_clear_irq0()
        self.mfrc630_clear_irq1()

        # enable the global IRQ for Rx done and Errors.
        self.mfrc630_write_reg(MFRC630_REG_IRQ0EN, MFRC630_IRQ0EN_RX_IRQEN | MFRC630_IRQ0EN_ERR_IRQEN)
        self.mfrc630_write_reg(MFRC630_REG_IRQ1EN, MFRC630_IRQ1EN_TIMER0_IRQEN)

        # configure timer
        timer_for_timeout = 0
        # Set timer to 221 kHz clock, start at the end of Tx.
        self.mfrc630_timer_set_control(timer_for_timeout, MFRC630_TCONTROL_CLK_211KHZ | MFRC630_TCONTROL_START_TX_END)

        # Frame waiting time: FWT = (256 x 16/fc) x 2 FWI
        # FWI defaults to four... so that would mean wait for a maximum of ~ 5ms
        self.mfrc630_timer_set_reload(timer_for_timeout, 1000)   # 1000 ticks of 5 usec is 5 ms.
        self.mfrc630_timer_set_value(timer_for_timeout, 1000)

        # Go into send, then straight after in receive.
        self.mfrc630_cmd_transceive([instruction])
        self.print_debug('Sending REQA')

        # block until we are done
        irq1_value = 0
        while not (irq1_value & (1 << timer_for_timeout)):
            irq1_value = self.mfrc630_irq1()
            if irq1_value & MFRC630_IRQ1_GLOBAL_IRQ:    # either ERR_IRQ or RX_IRQ
                break       # stop polling irq1 and quit the timeout loop

        self.print_debug('After waiting for answer')
        self.mfrc630_cmd_idle()

        # if no Rx IRQ, or if there's an error somehow, return 0
        irq0 = self.mfrc630_irq0()
        if (not (irq0 & MFRC630_IRQ0_RX_IRQ)) or (irq0 & MFRC630_IRQ0_ERR_IRQ):
            self.print_debug('No RX, irq1: %x irq0: %x' % (irq1_value, irq0))
            return 0

        return self.mfrc630_fifo_length()
        self.print_debug("rx_len:", rx_len)
        if rx_len == 2:  # ATQA should answer with 2 bytes
             res = self.mfrc630_read_fifo(rx_len)
             self.print_debug('ATQA answer:', res)
             return res
        return 0

    def mfrc630_print_block(self, data, len):
        if self._DEBUG:
            print(self.mfrc630_format_block(data, len))

    def mfrc630_format_block(self, data, len):
        if type(data) == bytearray:
            len_i = 0
            try:
                len_i = int(len)
            except:
                pass
            if (len_i > 0):
                return ' '.join('{:02x}'.format(x) for x in data[:len_i]).upper()
            else:
                return ' '.join('{:02x}'.format(x) for x in data).upper()
        else:
            self.print_debug("DATA has type: " + str(type(data)))
            try:
                return "Length: %d  Data: %s" % (len,binascii.hexlify(data,' '))
            except:
                return "Data: %s with Length: %s" % (str(data), len)


    def mfrc630_iso14443a_select(self, uid):

        self.print_debug("Starting select")

        self.mfrc630_cmd_idle()
        self.mfrc630_flush_fifo()

        # enable the global IRQ for Rx done and Errors.
        self.mfrc630_write_reg(MFRC630_REG_IRQ0EN, MFRC630_IRQ0EN_RX_IRQEN | MFRC630_IRQ0EN_ERR_IRQEN)
        self.mfrc630_write_reg(MFRC630_REG_IRQ1EN, MFRC630_IRQ1EN_TIMER0_IRQEN)  # only trigger on timer for irq1

        # configure a timeout timer, use timer 0.
        timer_for_timeout = 0

        # Set timer to 221 kHz clock, start at the end of Tx.
        self.mfrc630_timer_set_control(timer_for_timeout, MFRC630_TCONTROL_CLK_211KHZ | MFRC630_TCONTROL_START_TX_END)
        # Frame waiting time: FWT = (256 x 16/fc) x 2 FWI
        # FWI defaults to four... so that would mean wait for a maximum of ~ 5ms

        self.mfrc630_timer_set_reload(timer_for_timeout, 1000)  # 1000 ticks of 5 usec is 5 ms.
        self.mfrc630_timer_set_value(timer_for_timeout, 1000)

        for cascade_level in range(1, 4):
            self.print_debug("Starting cascade level: %d" % cascade_level)
            cmd = 0
            known_bits = 0  # known bits of the UID at this level so far.
            send_req = bytearray(7)  # used as Tx buffer.
            uid_this_level = send_req[2:]
            message_length = 0
            if cascade_level == 1:
                cmd = MFRC630_ISO14443_CAS_LEVEL_1;
            elif cascade_level == 2:
                cmd = MFRC630_ISO14443_CAS_LEVEL_2;
            elif cascade_level == 3:
                cmd = MFRC630_ISO14443_CAS_LEVEL_3;

            # disable CRC in anticipation of the anti collision protocol
            self.mfrc630_write_reg(MFRC630_REG_TXCRCPRESET, MFRC630_RECOM_14443A_CRC | MFRC630_CRC_OFF)
            self.mfrc630_write_reg(MFRC630_REG_RXCRCCON, MFRC630_RECOM_14443A_CRC | MFRC630_CRC_OFF)

            # max 32 loops of the collision loop.
            for collision_n in range(0, 33):
                self.print_debug("CL: %d, coll loop: %d, kb %d long" % (cascade_level, collision_n, known_bits))
                self.mfrc630_print_block(uid_this_level, (known_bits + 8 - 1) / 8)
                # clear interrupts
                self.mfrc630_clear_irq0()
                self.mfrc630_clear_irq1()

                send_req[0] = cmd;
                send_req[1] = 0x20 + known_bits
                send_req[2:5] = uid_this_level[0:3]

                # Only transmit the last 'x' bits of the current byte we are discovering
                # First limit the txdatanum, such that it limits the correct number of bits.
                self.mfrc630_write_reg(MFRC630_REG_TXDATANUM, (known_bits % 8) | MFRC630_TXDATANUM_DATAEN)

                # ValuesAfterColl: If cleared, every received bit after a collision is
                # replaced by a zero. This function is needed for ISO/IEC14443 anticollision (0<<7).
                # We want to shift the bits with RxAlign
                rxalign = known_bits % 8;
                self.print_debug("Setting rx align to: %d" % rxalign)
                self.mfrc630_write_reg(MFRC630_REG_RXBITCTRL, (0 << 7) | (rxalign << 4))

                # then sent the send_req to the hardware,
                # (known_bits / 8) + 1): The ceiled number of bytes by known bits.
                # +2 for cmd and NVB.
                if ((known_bits % 8) == 0):
                    message_length = ((known_bits / 8)) + 2;
                else:
                    message_length = ((known_bits / 8) + 1) + 2;

                # Send message
                self.mfrc630_cmd_transceive(send_req[:int(message_length)])

                # block until we are done
                irq1_value = 0
                while not (irq1_value & (1 << timer_for_timeout)):
                    irq1_value = self.mfrc630_irq1()
                    # either ERR_IRQ or RX_IRQ or Timer
                    if (irq1_value & MFRC630_IRQ1_GLOBAL_IRQ):
                        break  # stop polling irq1 and quit the timeout loop.

                self.mfrc630_cmd_idle()

                # next up, we have to check what happened.
                irq0 = self.mfrc630_irq0()
                error = self.mfrc630_read_reg(MFRC630_REG_ERROR)
                coll = self.mfrc630_read_reg(MFRC630_REG_RXCOLL)
                self.print_debug("irq0: %x coll: %x error: %x " % (irq0, coll, error))
                collision_pos = 0
                if irq0 and MFRC630_IRQ0_ERR_IRQ:  # some error occured.
                    self.print_debug("some error occured.")
                    # Check what kind of error.
                    if (error & MFRC630_ERROR_COLLDET):
                        # A collision was detected...
                        if (coll & (1 << 7)):
                            collision_pos = coll & (~(1 << 7))
                            self.print_debug("Collision at %x", collision_pos)
                            # This be a true collision... we have to select either the address
                            # with 1 at this position or with zero
                            # ISO spec says typically a 1 is added, that would mean:
                            # uint8_t selection = 1;

                            # However, it makes sense to allow some kind of user input for this, so we use the
                            # current value of uid at this position, first index right byte, then shift such
                            # that it is in the rightmost position, ten select the last bit only.
                            # We cannot compensate for the addition of the cascade tag, so this really
                            # only works for the first cascade level, since we only know whether we had
                            # a cascade level at the end when the SAK was received.
                            choice_pos = known_bits + collision_pos
                            selection = (uid[((choice_pos + (cascade_level - 1) * 3) / 8)] >> ((choice_pos) % 8)) & 1

                            # We just OR this into the UID at the right position, later we
                            # OR the UID up to this point into uid_this_level.
                            uid_this_level[((choice_pos) / 8)] |= selection << ((choice_pos) % 8)
                            known_bits = known_bits + 1  # add the bit we just decided.
                            self.print_debug("Known Bits: %d" % known_bits)

                            self.print_debug("uid_this_level now kb %d long: " % known_bits)
                            self.mfrc630_print_block(uid_this_level, 10)
                        else:
                            # Datasheet of mfrc630:
                            # bit 7 (CollPosValid) not set:
                            # Otherwise no collision is detected or
                            # the position of the collision is out of the range of bits CollPos.
                            self.print_debug("Collision but no valid collpos.")
                            collision_pos = 0x20 - known_bits
                    else:
                        # we got data despite an error, and no collisions, that means we can still continue.
                        collision_pos = 0x20 - known_bits
                        self.print_debug("Got data despite error: %x, setting collision_pos to: %x" % (error, collision_pos))
                elif (irq0 & MFRC630_IRQ0_RX_IRQ):
                    # we got data, and no collisions, that means all is well.
                    self.print_debug("we got data, and no collisions, that means all is well.")
                    collision_pos = 0x20 - known_bits
                    self.print_debug("Got data, no collision, setting to: %x" % collision_pos)
                else:
                    # We have no error, nor received an RX. No response, no card?
                    self.print_debug("We have no error, nor received an RX. No response, no card?")
                    return 0

                self.print_debug("collision_pos: %x" % collision_pos)
                # read the UID Cln so far from the buffer.
                rx_len = self.mfrc630_fifo_length()
                buf = self.mfrc630_read_fifo(rx_len if rx_len < 5 else 5)

                self.print_debug("Fifo %d long" % rx_len)
                self.mfrc630_print_block(buf, rx_len)

                self.print_debug("uid_this_level kb %d long: " % known_bits)
                self.mfrc630_print_block(uid_this_level, (known_bits + 8 - 1) / 8)

                # move the buffer into the uid at this level, but OR the result such that
                # we do not lose the bit we just set if we have a collision.
                for rbx in range(0, rx_len):
                    uid_this_level[int(known_bits / 8) + rbx] = uid_this_level[int(known_bits / 8) + rbx] | buf[rbx]
                self.print_debug("uid_this_level after reading buffer (known_bits=%d):" % known_bits)
                self.mfrc630_print_block(uid_this_level, 0)
                self.print_debug("known_bits: %x + collision_pos: %x = %x" % (known_bits, collision_pos, known_bits + collision_pos))
                known_bits = known_bits + collision_pos
                self.print_debug("known_bits: %x" % known_bits)

                if known_bits >= 32:
                    self.print_debug("exit collision loop: uid_this_level kb %d long: " % known_bits);
                    self.mfrc630_print_block(uid_this_level, 10)
                    break;  # done with collision loop
                # end collission loop

            # check if the BCC matches
            bcc_val = uid_this_level[4]  # always at position 4, either with CT UID[0-2] or UID[0-3] in front.
            bcc_calc = uid_this_level[0] ^ uid_this_level[1] ^ uid_this_level[2] ^ uid_this_level[3]
            self.print_debug("BCC calc: %x" % bcc_calc)
            if (bcc_val != bcc_calc):
                self.print_debug("Something went wrong, BCC does not match.")
                return 0

            # clear interrupts
            self.mfrc630_clear_irq0()
            self.mfrc630_clear_irq1()

            send_req[0] = cmd
            send_req[1] = 0x70
            send_req[2] = uid_this_level[0]
            send_req[3] = uid_this_level[1]
            send_req[4] = uid_this_level[2]
            send_req[5] = uid_this_level[3]
            send_req[6] = bcc_calc
            message_length = 7

            # Ok, almost done now, we re-enable the CRC's
            self.mfrc630_write_reg(MFRC630_REG_TXCRCPRESET, MFRC630_RECOM_14443A_CRC | MFRC630_CRC_ON)
            self.mfrc630_write_reg(MFRC630_REG_RXCRCCON, MFRC630_RECOM_14443A_CRC | MFRC630_CRC_ON)

            # reset the Tx and Rx registers (disable alignment, transmit full bytes)
            self.mfrc630_write_reg(MFRC630_REG_TXDATANUM, (known_bits % 8) | MFRC630_TXDATANUM_DATAEN)
            rxalign = 0
            self.mfrc630_write_reg(MFRC630_REG_RXBITCTRL, (0 << 7) | (rxalign << 4))

            # actually send it!
            self.mfrc630_cmd_transceive(send_req)
            self.print_debug("send_req %d long: " % message_length)
            self.mfrc630_print_block(send_req, message_length)

            # Block until we are done...
            irq1_value = 0
            while not (irq1_value & (1 << timer_for_timeout)):
                irq1_value = self.mfrc630_irq1()
                if (irq1_value & MFRC630_IRQ1_GLOBAL_IRQ):  # either ERR_IRQ or RX_IRQ
                    break  # stop polling irq1 and quit the timeout loop.
            self.mfrc630_cmd_idle()

            # Check the source of exiting the loop.
            irq0_value = self.mfrc630_irq0()
            self.print_debug("irq0: %x" % irq0_value)
            if irq0_value & MFRC630_IRQ0_ERR_IRQ:
                # Check what kind of error.
                error = self.mfrc630_read_reg(MFRC630_REG_ERROR)
                self.print_debug("error: %x" % error)
                if error & MFRC630_ERROR_COLLDET:
                    # a collision was detected with NVB=0x70, should never happen.
                    self.print_debug("a collision was detected with NVB=0x70, should never happen.")
                    return 0
            # Read the sak answer from the fifo.
            sak_len = self.mfrc630_fifo_length()
            self.print_debug("sak_len: %x" % sak_len)
            if sak_len != 1:
                return 0

            sak_value = self.mfrc630_read_fifo(sak_len)

            self.print_debug("SAK answer: ")
            self.mfrc630_print_block(sak_value, 1)

            if (sak_value[0] & (1 << 2)):
                # UID not yet complete, continue with next cascade.
                # This also means the 0'th byte of the UID in this level was CT, so we
                # have to shift all bytes when moving to uid from uid_this_level.
                for UIDn in range(0, 3):
                    # uid_this_level[UIDn] = uid_this_level[UIDn + 1];
                    uid[(cascade_level - 1) * 3 + UIDn] = uid_this_level[UIDn + 1]
            else:
                # Done according so SAK!
                # Add the bytes at this level to the UID.
                for UIDn in range(0, 4):
                    uid[(cascade_level - 1) * 3 + UIDn] = uid_this_level[UIDn];

                # Finally, return the length of the UID that's now at the uid "pointer".
                return cascade_level * 3 + 1

        self.print_debug("Exit cascade loop nr. %d: " % cascade_level)
        self.mfrc630_print_block(uid, 10)

        return 0  # getting a UID failed.

    def mfrc630_MF_auth(self, uid, key_type, block):
        # Enable the right interrupts.

        # configure a timeout timer.
        timer_for_timeout = 0  # should match the enabled interrupt.

        # According to datasheet Interrupt on idle and timer with MFAUTHENT, but lets
        # include ERROR as well.
        self.mfrc630_write_reg(MFRC630_REG_IRQ0EN, MFRC630_IRQ0EN_IDLE_IRQEN | MFRC630_IRQ0EN_ERR_IRQEN)
        self.mfrc630_write_reg(MFRC630_REG_IRQ1EN, MFRC630_IRQ1EN_TIMER0_IRQEN)  # only trigger on timer for irq1

        # Set timer to 221 kHz clock, start at the end of Tx.
        self.mfrc630_timer_set_control(timer_for_timeout, MFRC630_TCONTROL_CLK_211KHZ | MFRC630_TCONTROL_START_TX_END)
        # Frame waiting time: FWT = (256 x 16/fc) x 2 FWI
        # FWI defaults to four... so that would mean wait for a maximum of ~ 5ms

        self.mfrc630_timer_set_reload(timer_for_timeout, 2000)  # 2000 ticks of 5 usec is 10 ms.
        self.mfrc630_timer_set_value(timer_for_timeout, 2000)

        irq1_value = 0

        self.mfrc630_clear_irq0()  # clear irq0
        self.mfrc630_clear_irq1()  # clear irq1

        # start the authentication procedure.
        self.mfrc630_cmd_auth(key_type, block, uid)

        # block until we are done
        while not (irq1_value & (1 << timer_for_timeout)):
            irq1_value = self.mfrc630_irq1()
            if (irq1_value & MFRC630_IRQ1_GLOBAL_IRQ):
                break  # stop polling irq1 and quit the timeout loop.

        if (irq1_value & (1 << timer_for_timeout)):
            # this indicates a timeout
            return 0  # we have no authentication

        # status is always valid, it is set to 0 in case of authentication failure.
        status = self.mfrc630_read_reg(MFRC630_REG_STATUS)
        return (status & MFRC630_STATUS_CRYPTO1_ON)

    def mfrc630_MF_deauth(self):
      self.mfrc630_write_reg(MFRC630_REG_STATUS, 0)

    def format_block(self, block, length):
        ret_val = ""
        for i in range(0, length):
            if (block[i] < 16):
                ret_val += ("0%x " % block[i])
            else:
                ret_val += ("%x " % block[i])
        return ret_val.upper()
