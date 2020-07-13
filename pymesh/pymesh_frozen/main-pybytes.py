import time
import pycom

# todo: add try/except for checking pybytes object exists
pymesh = pybytes.__pymesh.__pymesh

print("Set maximum debug level, disable debug using pymesh.debug_level(0)")
pymesh.debug_level(5)

while not pymesh.is_connected():
    print(pymesh.status_str())
    time.sleep(3)

print(pymesh.status_str())
# send message to the Node having MAC address 5
pymesh.send_mess(18, "Hello World")

print("done Pymesh init, CLI is started, h - help/command list, stop - CLI will be stopped")
pymesh.cli_start()

# send a packet to Pybytes, thru the BR (if any enabled)
# pybytes.send_signal(100, "Hello from device" + str(pymesh.mac()))
