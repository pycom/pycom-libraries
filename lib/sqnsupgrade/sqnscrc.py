# -*- python -*-
#################################################################
#
# Module : CRC
# Purpose: CRC calculation
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
import sqnscodec as codec

# -------------------------------------------------// Fletcher /_________________________________
def fletcher32 (data):
    l = len(data)

    index = 0
    s1 = s2 = 0xFFFF
    while l > 1:
        qty = 720 if l > 720 else (l & ~1)
        l -= qty

        qty += index
        while index < qty:
            word = codec.decode.u16(data[index:index+2])
            s1 += word
            s2 += s1

            index += 2

        s1 = (s1 & 0xFFFF) + (s1 >> 16)
        s2 = (s2 & 0xFFFF) + (s2 >> 16)

    if (l & 1):
        s1 += ord(data[index]) << 8
        s2 += s1

        s1 = (s1 & 0xFFFF) + (s1 >> 16)
        s2 = (s2 & 0xFFFF) + (s2 >> 16)

    s1 = (s1 & 0xFFFF) + (s1 >> 16)
    s2 = (s2 & 0xFFFF) + (s2 >> 16)

    return (s2 << 16) | s1
