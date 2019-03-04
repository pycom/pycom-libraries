from network import LoRa
import ubinascii
from loramesh import Loramesh
import pycom
import time
import socket
import struct

BORDER_ROUTER_HEADER_FORMAT = '!BHHHHHHHHH'

pycom.wifi_on_boot(False)
pycom.heartbeat(False)
border_router_net = "2001:dead:beef:caff::/64"

lora = LoRa(mode=LoRa.LORA, region=LoRa.EU868, bandwidth=LoRa.BW_125KHZ, sf=7)
#mesh = lora.Mesh()
MAC = str(ubinascii.hexlify(lora.mac()))[2:-1]
print("LoRa MAC: %s"%MAC)

mesh = Loramesh(lora)

# waiting until it connected to Mesh network
while True:
    mesh.led_state()
    print("%d: State %s, single %s"%(time.time(), mesh.cli('state'), mesh.cli('singleton')))
    time.sleep(2)
    if not mesh.is_connected():
        continue

    print('Neighbors found: %s'%mesh.neighbors())
    print('IPs: %s'%mesh.mesh.ipaddr())
    print('BRs: %s'%mesh.mesh.border_router())
    break

#add BR
if int(MAC, 16) == 8:
    if len(mesh.mesh.border_router()) == 0:
        mesh.mesh.border_router(border_router_net, 1)
        print("Set Border Router with prefix %s"%border_router_net)

# create UDP socket for Border Router interface
br_socket = socket.socket(socket.AF_LORA, socket.SOCK_RAW)
myport = 1234
print("Please wait until BR gets propagated to the Leader ...")
while True:
    ip = mesh.ip(border_router_net)
    #ip = mesh.ip()
    if ip is not None:
        br_socket.bind((ip, myport))
        #s.bind(myport)
        print("Created socked for (%s, %d)"%(ip, myport))
        break
    time.sleep(1)

eid_sock = socket.socket(socket.AF_LORA, socket.SOCK_RAW)
myport = 1235
ip = mesh.ip()# ipv6 EID
if ip is not None:
    eid_sock.bind((ip, myport))
    #s.bind(myport)
    print("Created socked for (%s, %d)"%(ip, myport))

# handler responisble for receiving packets on UDP Pymesh socket
def receive_pack(dummy):
    # listen for incomming packets
    sock = eid_sock
    while True:
        rcv_data, rcv_addr = sock.recvfrom(128)
        if len(rcv_data) == 0:
            rcv_data, rcv_addr = br_socket.recvfrom(128)
            if len(rcv_data) == 0:
                break
            print("Data from Border Router socket")
            sock = br_socket
        rcv_ip = rcv_addr[0]
        rcv_port = rcv_addr[1]
        print('Incomming %d bytes from %s (port %d)'%(len(rcv_data), rcv_ip, rcv_port))
        if sock == br_socket and len(rcv_data) >= struct.calcsize(BORDER_ROUTER_HEADER_FORMAT):
            br_header = struct.unpack(BORDER_ROUTER_HEADER_FORMAT, rcv_data)
            print("IP dest: %X:%X:%X:%X:%X:%X:%X:%X (port %d)"%(
                br_header[1],br_header[2],br_header[3],br_header[4],
                br_header[5],br_header[6],br_header[7],br_header[8], br_header[9]))
            print(rcv_data[struct.calcsize(BORDER_ROUTER_HEADER_FORMAT):])
        else:
            print(rcv_data)
        if  not rcv_data.startswith("ACK"):
            print("Sent ACK back")
            sock.sendto('ACK', (rcv_ip, rcv_port))

mesh.mesh.rx_cb(receive_pack, None)
