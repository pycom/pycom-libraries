# -*- python -*-
#################################################################
#
# Module : CODEC
# Purpose: Base encoders/decoders
#
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
import struct, array

LITTLE_ENDIAN = "<"
NATIVE_ENDIAN = "="
BIG_ENDIAN = ">"

# -------------------------------------------------// Utility /__________________________________
class encode:
    @staticmethod
    def u32 (value, endian = BIG_ENDIAN):
        return array.array("c", struct.pack(endian + "I", value))

    @staticmethod
    def s32 (value, endian = BIG_ENDIAN):
        if value < 0:
            value = 0x100000000 + value
        return encode.u32(value, endian)

    @staticmethod
    def u16 (value, endian = BIG_ENDIAN):
        return array.array("c", struct.pack(endian + "H", value))

    @staticmethod
    def u8 (value, endian = None):
        return array.array("c", chr(value))

    @staticmethod
    def string (value, endian = None):
        return array.array("c", value + "\x00")

class decode:
    @staticmethod
    def u32 (value, endian = BIG_ENDIAN):
        return struct.unpack(endian + "I", value)[0]

    @staticmethod
    def s32 (value, endian = BIG_ENDIAN):
        v = decode.u32(value, endian)
        if v & (1 << 31):
            return v - 0x100000000
        return v

    @staticmethod
    def u16 (value, endian = BIG_ENDIAN):
        return struct.unpack(endian + "H", value)[0]

    @staticmethod
    def u8 (value, endian = None):
        return ord(value)

    @staticmethod
    def string (value, endian = None):
        offset = 0
        str = ""
        c = value[offset]
        while c != '\x00':
            offset += 1
            str += c
            c = value[offset]

        return str

