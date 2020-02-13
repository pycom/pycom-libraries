import time
import pycom

# 2 = test pybytes OTA feature
__VERSION__ = 3

try:
    from pymesh_config import PymeshConfig
except:
    from _pymesh_config import PymeshConfig

try:
    from pymesh import Pymesh
except:
    from _pymesh import Pymesh

# LoRa mac that will be self-defined as Border Routers
MAC_BR = {2,4}

print("Scripts version ", __VERSION__)

if 'pybytes' not in globals():
    pybytes = None

def new_message_cb(rcv_ip, rcv_port, rcv_data):
    ''' callback triggered when a new packet arrived '''
    print('Incoming %d bytes from %s (port %d):' %
            (len(rcv_data), rcv_ip, rcv_port))
    print(rcv_data)

    # user code to be inserted, to send packet to the designated Mesh-external interface
    for _ in range(3):
        pycom.rgbled(0x888888)
        time.sleep(.2)
        pycom.rgbled(0)
        time.sleep(.1)
    return

def new_br_message_cb(rcv_ip, rcv_port, rcv_data, dest_ip, dest_port):
    ''' callback triggered when a new packet arrived for the current Border Router,
    having destination an IP which is external from Mesh '''
    print('Incoming %d bytes from %s (port %d), to external IPv6 %s (port %d)' %
            (len(rcv_data), rcv_ip, rcv_port, dest_ip, dest_port))
    print(rcv_data)

    for _ in range(2):
        pycom.rgbled(0x0)
        time.sleep(.1)
        # pycom.rgbled(0x001010)
        pycom.rgbled(0x663300)
        # time.sleep(.2)

    if pybytes is not None and pybytes.isconnected():
        pkt = 'BR %d B from %s (%d), to %s ( %d): %s'%(len(rcv_data), rcv_ip, rcv_port, dest_ip, dest_port, str(rcv_data))
        pybytes.send_signal(1, pkt)

    return

pycom.heartbeat(False)

# read config file, or set default values
pymesh_config = PymeshConfig.read_config()

#initialize Pymesh
pymesh = Pymesh(pymesh_config, new_message_cb)

# mac = pymesh.mac()
# if mac > 10:
#     pymesh.end_device(True)
# elif mac == 5:
#     pymesh.leader_priority(255)

while not pymesh.is_connected():
    print(pymesh.status_str())
    time.sleep(3)

# send message to the Node having MAC address 5
pymesh.send_mess(2, "Hello World")


print("done Pymesh init, forever loop, exit/stop with Ctrl+C multiple times")
# set BR with callback
if pybytes is not None and pybytes.isconnected():
    pybytes.send_signal(1, "RESTART")

pyb_port = pymesh.mac() & 0xFFFF
pyb_ip = '1:2:3::' + hex(pyb_port)[2:]
pkt_start = "Hello, from " + str(pymesh.mac()) + ", time "

br_enabled = False

while True:
    # add current node as Border Router, with a priority and a message handler callback

    free_mem = pycom.get_free_heap()

    if pymesh.mac() in MAC_BR:
        if pybytes is not None and pybytes.isconnected():
            if not br_enabled:
                br_enabled = True
                print("Set as BR")
                pymesh.br_set(PymeshConfig.BR_PRIORITY_NORM, new_br_message_cb)

            pybytes.send_signal(1, str(pymesh.mac()) +" : " + str(time.time()) + "s, "+ str(free_mem))
            print("Send to Pyb,", free_mem)
        else: # not connected anymore to pybytes
            if br_enabled:
                br_enabled = False
                print("Remove as BR")
                pymesh.br_remove()
    else: # not MAC_BR
        pkt = pkt_start + str(time.time()) + ", mem " + str(free_mem)
        pymesh.send_mess_external(pyb_ip, pyb_port, pkt)
        print("Sending to BR: ", pkt)

    time.sleep(20)
