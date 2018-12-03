from network import LoRa
import socket
import time
import utime
import ubinascii
import pycom

__version__ = '1'

class Loramesh:
    """ Class for using Lora Mesh - openThread """

    STATE_NOT_CONNECTED = const(0)
    STATE_CHILD = const(1)
    STATE_ROUTER = const(2)
    STATE_LEADER = const(3)
    #STATE_CHILD_SINGLE = const(4)
    STATE_LEADER_SINGLE = const(4)

    # rgb LED color for each state: not connected, child, router, leader and single leader
    RGBLED = [0x0A0000, 0x0A0A0A, 0x000A00, 0x00000A, 0x07070A]

    # address to be used for multicasting
    MULTICAST_MESH_ALL = 'ff03::1'
    MULTICAST_MESH_FTD = 'ff03::2'

    MULTICAST_LINK_ALL = 'ff02::1'
    MULTICAST_LINK_FTD = 'ff02::2'

    def __init__(self, lora=None):
        """ Constructor """
        if lora is None:
            self.lora = LoRa(mode=LoRa.LORA, region=LoRa.EU868, bandwidth=LoRa.BW_125KHZ, sf=7)
        else:
            self.lora = lora
        self.lora.mesh()
        self.rloc = ''
        self.ip_eid = ''
        self.ip_link = ''
        self.single = True
        self.state_id = STATE_NOT_CONNECTED

    def _update_ips(self):
        """ Updates all the unicast IPv6 of the Thread interface """
        ip_all = self.lora.cli('ipaddr')
        ips = ip_all.split('\r\n')
        try:
            rloc16 = int(self.lora.cli('rloc16'), 16)
        except Exception:
            rloc16 = 0xFFFF
        for line in ips:
            if line.startswith('fd'):
                # Mesh-Local unicast IPv6
                if int(line.split(':')[-1], 16) == rloc16:
                    # found RLOC
                    # RLOC IPv6 has x:x:x:x:0:ff:fe00:RLOC16
                    self.rloc = line
                elif ':0:ff:fe00:' not in line:
                    # found Mesh-Local EID
                    self.ip_eid = line
            elif line.startswith('fe80'):
                # Link-Local
                self.ip_link = line

    def is_connected(self):
        """ Returns true if it is connected if its Child, Router or Leader """
        connected = False
        state = self.state()
        if state == STATE_CHILD or state == STATE_ROUTER or state == STATE_LEADER:
            connected = True
        return connected

    def state(self):
        """ Returns the Thread role """
        state_code = STATE_NOT_CONNECTED
        try:
            state = self.lora.cli('state')

            if state.startswith('child'):
                state_code = STATE_CHILD
            elif state.startswith('router'):
                state_code = STATE_ROUTER
            elif state.startswith('leader'):
                state_code = STATE_LEADER
                self.single = False
                single_str = self.lora.cli('singleton')
                if single_str.startswith('true'):
                    self.single = True
                    state_code = STATE_LEADER_SINGLE

            self.state_id = state_code
        except Exception:
                pass
        return state_code

    def led_state(self):
        """ Sets the LED according to the Thread role """
        pycom.rgbled(self.RGBLED[self.state()])

    def ip(self):
        """ Returns the IPv6 RLOC """
        self._update_ips()
        return self.rloc

    def parent_ip(self):
        """ Returns the IP of the parent, if it's child node """
        ip = None
        state = self.state()
        if state == STATE_CHILD or state == STATE_ROUTER:
            try:
                ip_words = self.ip().split(':')
                parent_rloc = int(self.lora.cli('parent').split('\r\n')[1].split(' ')[1], 16)
                ip_words[-1] = hex(parent_rloc)[2:]
                ip = ':'.join(ip_words)
            except Exception:
                pass
        return ip

    def neighbors_ip(self):
        """ Returns a list with IP of the neighbors (children, parent, other routers) """
        state = self.state()
        neigh = []
        if state == STATE_ROUTER or state == STATE_LEADER:
            ip_words = self.ip().split(':')
            # obtain RLOC16 neighbors
            neighbors = self.lora.cli('neighbor list').split(' ')
            for rloc in neighbors:
                if len(rloc) == 0:
                    continue
                try:
                    ip_words[-1] = str(rloc[2:])
                    nei_ip = ':'.join(ip_words)
                    neigh.append(nei_ip)
                except Exception:
                        pass
        elif state == STATE_CHILD:
            neigh.append(self.parent_ip())
        return neigh

    def ipaddr(self):
        """ Returns a list with all unicast IPv6 """
        return self.lora.cli('ipaddr').split('\r\n')

    def cli(self, command):
        """ Simple wrapper for OpenThread CLI """
        return self.lora.cli(command)

    def ping(self, ip):
        """ Returns ping return time, to an IP """
        res = self.cli('ping ' + ip)
        # '8 bytes from fdde:ad00:beef:0:0:ff:fe00:e000: icmp_seq=2 hlim=64 time=236ms\r\n'
        # 'Error 6: Parse\r\n'
        # no answer
        ret_time = -1
        try:
            ret_time = int(res.split('time=')[1].split('ms')[0])
        except Exception:
            pass
        return ret_time

    def blink(self, num = 3, period = .5, color = None):
        """ LED blink """
        if color is None:
            color = self.RGBLED[self.state()]
        for i in range(0, num):
            pycom.rgbled(0)
            time.sleep(period)
            pycom.rgbled(color)
            time.sleep(period)
        self.led_state()
