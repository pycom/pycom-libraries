import pycom
import time

try:
    from pymesh_config import PymeshConfig
except:
    from _pymesh_config import PymeshConfig

try:
    from pymesh import Pymesh
except:
    from _pymesh import Pymesh

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


pycom.heartbeat(False)

# read config file, or set default values
pymesh_config = PymeshConfig.read_config()

#initialize Pymesh
pymesh = Pymesh(pymesh_config, new_message_cb)

while not pymesh.is_connected():
    print(pymesh.status_str())
    time.sleep(3)

# send message to the Node having MAC address 5
pymesh.send_mess(20, "Hello World")

print("done Pymesh init, forever loop, exit/stop with Ctrl+C multiple times")

from lorawan import Lorawan
lorawan = Lorawan()
t0 = time.time()

while True:
    if time.time() - t0 > 60:
        pymesh.pause()

        lorawan.send()

        pymesh.resume()
        t0 = time.time()
    if time.time() - t0 > 35:
        pymesh.send_mess(20, "heloo again, #22 here, " + str(time.time()))

    time.sleep(5)
