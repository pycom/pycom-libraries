
# - Protocol types
MQTTv3_1 = 3
MQTTv3_1_1 = 4

# - OfflinePublishQueueing drop behavior
DROP_OLDEST = 0
DROP_NEWEST = 1

# Message types
MSG_CONNECT = 0x10
MSG_CONNACK = 0x20
MSG_PUBLISH = 0x30
MSG_PUBACK = 0x40
MSG_PUBREC = 0x50
MSG_PUBREL = 0x60
MSG_PUBCOMP = 0x70
MSG_SUBSCRIBE = 0x80
MSG_SUBACK = 0x90
MSG_UNSUBSCRIBE = 0xA0
MSG_UNSUBACK = 0xB0
MSG_PINGREQ = 0xC0
MSG_PINGRESP = 0xD0
MSG_DISCONNECT = 0xE0

# Connection state
STATE_CONNECTED = 0x01
STATE_CONNECTING = 0x02
STATE_DISCONNECTED = 0x03

class UUID:
    int_ = int
    bytes_ = bytes

    def __init__(self, bytes=None, version=None):

        self._int = UUID.int_.from_bytes(bytes, 'big')

        self._int &= ~(0xc000 << 48)
        self._int |= 0x8000 << 48
        self._int &= ~(0xf000 << 64)
        self._int |= version << 76

    @property
    def urn(self):
        return 'urn:uuid:' + str(self)
