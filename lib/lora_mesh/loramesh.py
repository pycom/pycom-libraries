from network import LoRa
import socket
import time
import utime
import ubinascii
import pycom

__version__ = '2'

class Loramesh:
    """ Class for using Lora Mesh - openThread """

    STATE_DISABLED = const(0)
    STATE_DETACHED = const(1)
    STATE_CHILD = const(2)
    STATE_ROUTER = const(3)
    STATE_LEADER = const(4)
    STATE_LEADER_SINGLE = const(5)

    # rgb LED color for each state: disabled, detached, child, router, leader and single leader
    RGBLED = [0x0A0000, 0x0A0000, 0x0A0A0A, 0x000A00, 0x0A000A, 0x000A0A]

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
        self.mesh = self.lora.Mesh()
        self.rloc = ''
        self.ip_eid = ''
        self.ip_link = ''
        self.single = True
        self.state = STATE_DISABLED
        self.ip_others = []

    def _state_update(self):
        """ Returns the Thread role """
        self.state = self.mesh.state()
        if self.state < 0:
            self.state = self.STATE_DISABLED
        return self.state

    def _rloc_ip_net_addr(self):
        """ returns the family part of RLOC IPv6, without last word (2B) """
        self.net_addr = ':'.join(self.rloc.split(':')[:-1]) + ':'
        return self.net_addr

    def _update_ips(self):
        """ Updates all the unicast IPv6 of the Thread interface """
        self.ip_others = []
        ips = self.mesh.ipaddr()
        self.rloc16 = self.mesh.rloc()
        for line in ips:
            if line.startswith('fd'):
                # Mesh-Local unicast IPv6
                try:
                    addr = int(line.split(':')[-1], 16)
                except Exception:
                    continue
                if addr == self.rloc16:
                    # found RLOC
                    # RLOC IPv6 has x:x:x:x:0:ff:fe00:RLOC16
                    self.rloc = line
                elif ':0:ff:fe00:' not in line:
                    # found Mesh-Local EID
                    self.ip_eid = line
            elif line.startswith('fe80'):
                # Link-Local
                self.ip_link = line
            else:
                self.ip_others.append(line)

    def is_connected(self):
        """ Returns true if it is connected as either Child, Router or Leader """
        connected = False
        self.state = self.mesh.state()
        if self.state in (STATE_CHILD, STATE_ROUTER, STATE_LEADER, STATE_LEADER_SINGLE):
            connected = True
        return connected

    def led_state(self):
        """ Sets the LED according to the Thread role """
        if self.state == STATE_LEADER and self.mesh.single():
            pycom.rgbled(self.RGBLED[self.STATE_LEADER_SINGLE])
        else:
            pycom.rgbled(self.RGBLED[self.state])

    # returns the IP ML-EID or the ip having this prefix
    def ip(self, prefix = None):
        """ Returns the IPv6 RLOC """
        ip = self._update_ips()
        if prefix is None:
            return self.ip_eid
        # we need to check al IPs from self.ip_others that may start with prefix
        p = prefix.split("::")[0]
        for ip in self.ip_others:
            if ip.startswith(p):
                return ip
        return None

    def neighbors(self):
        """ Returns a list with all properties of the neighbors """
        return self.mesh.neighbors()

    def neighbors_ip(self):
        """ Returns a list with IPv6 (as strings) of the neighbors """
        neighbors = self.neighbors()
        nei_list = []
        net_ip = self._rloc_ip_net_addr()
        if neighbors is not None:
            for nei_rec in neighbors:
                nei_ip = net_ip + hex(nei_rec.rloc16)[2:]
                nei_list.append(nei_ip)
        return nei_list

    def ipaddr(self):
        """ Returns a list with all unicast IPv6 """
        return self.mesh.ipaddr()

    def cli(self, command):
        """ Simple wrapper for OpenThread CLI """
        return self.mesh.cli(command)

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
            color = self.RGBLED[self.state]
        for i in range(0, num):
            pycom.rgbled(0)
            time.sleep(period)
            pycom.rgbled(color)
            time.sleep(period)
        self.led_state()
