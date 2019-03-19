# Pymesh micropython code

This project exemplifies the use of Pycom's proprietary LoRa Mesh network - **Pymesh**.
These scripts were created and tested on Lopy4 and Fipy, using the minimum release as [1.20.0.rc8](https://forum.pycom.io/topic/4499/firmware-release-candidate-v1-20-0-rc8).

Official Pymesh docs: https://docs.pycom.io/firmwareapi/pycom/network/lora/pymesh.html

Simple Pymesh example: https://docs.pycom.io/tutorials/lora/lora-mesh.html

Forum Pymesh announcements: https://forum.pycom.io/topic/4449/pymesh-updates

## Overview
These scripts were created to prototype different features of Pymesh.

They are quite monolithic, as they were developed on par with firmware Pymesh development. Multiple improvement are foreseen to be further performed, into areas like modularity (BLE RPC is the main candidate). Also lots of code is executed in micropython threads, which have limited memory (they should be moved in the *main loop*). Maybe queues for RX/TX on Pymesh should be added, with automatic retransmissions until ACK.

### Important features
* Start Pymesh over LoRa on 863Mhz, bandwidth 250kHz, spreading-factor 7 (check MeshInternal constructor).
* Pymesh parameters are automatically saved in NVM, so in the next restart/deepsleep, the node will try to maintain its IP addresses and connections with neighbour nodes.
* Start BLE server with name `PyGo (mac: <LoRa MAC>`
  * BLE is used with an RPC protocol, packed using `msgpack` library .
* Internal CLI for controlling/triggering Pymesh features, as explained bellow.

## Color coding LED

The LED color represents the state of the node in the Mesh network.

    Magenta            - LEADER
    Green              - ROUTER
    White              - CHILD,
    Red                - Searching / Detached from any Pymesh
    Cyan               - SINGLE LEADER (no other Router in the same Pymesh)

## Internal CLI
```
>mac
1
```
Shows LoRa MAC, this address is used as unique identifier in the Pymesh. Bellow there's a section on how to set MAC specific MAC address (useful for debugging, the MAC could be consecutive small numbers like `0x1`, `0x2`, `...`)

```
>mml
mesh_mac_list  [1, 6, 2]
```
Shows the list of all MAC Nodes included into Pymesh. Inquires Leader if doesn't have this info (or if too old). In about 5 sec, a new call will return the latest list.

```
>mp
Send pack: 0xF3 to IP fdde:ad00:beef:0:0:ff:fe00:fc00
last_mesh_pairs [[2, 6, -87], [1, 6, -77]]
```
Shows Mesh Pairs list, with each direct connected nodes (by their MAC address) and the averaged RSSI value.

```
>mni
last_mesh_node_info {1: {"ip": 2048, "l": {"lng": 5.45313, "lat": 51.45}, "a": 10, "r": 3, "nn": 1, "nei": [[6, 55296, 3, -76, 23]]}, 6: {"ip": 55296, "l": {"lng": 5.45313, "lat": 51.45}, "a": 7, "r": 3, "nn": 2, "nei": [[2, 50176, 3, -89, 28], [1, 2048, 3, -77, 23]]}, 2: {"ip": 50176, "l": {"lng": 5.45313, "lat": 51.45}, "a": 7, "r": 3, "nn": 1, "nei": [[6, 55296, 3, -86, 25]]}}
```
Shows the properties for all the nodes in this Pymesh, together with its neighbors.

```
>s
(to)<1
(txt)<Hello World!
1945688: Send Msg ---------------------->>>>>>>>
Added new message for 1: Hello World!
Send pack: 0x10 to IP fdde:ad00:beef:0::1
True
>Incoming 13 bytes from fdde:ad00:beef:0:f67b:3d1e:f07:8341 (port 1234):
PACK_MESSAGE_ACK received
1945883 =================  ACK RECEIVED :) :) :)
```
Sends text messages to another Node inside Pymesh. The messaging waits for ACK from the destination node. If not received, it's resent after minimum 15 seconds.

*Sorry for the messy output and debug info.*

```
ws
(to)<1
ACK? mac 1, id 12345 => 1
True
```
Shows if a message was acknowledged by the destination Node.

```
>rm
{'b': (b'Hello World!',), 'id': 12345, 'ts': 3301, 'from': 6}
```
Shows the received messages.

```
f
(MAC to)<1
(packsize)<500
(filename, Enter for dog.jpg)<
...
Incoming 6 bytes from fdde:ad00:beef:0:160b:8542:2190:c864 (port 1234):
PACK_FILE_SEND_ACK received
6165 Bytes sent, time:   27 sec
Done sending 6165 B in 27 sec
```
Sends a file already stored in `/flash` (by default `/flash/dog.jpg`), specifying to which Node and in what chunk size (it can't be bigger than 500 Bytes, limit set in firmware).

At destination, the file is stored as `/flash/dog_rcv.jpg`.
Picture files could be stored on Lopy4/Fipy using either Pymakr (over USB) or FTP.

*The file transfer is done naively, the file is not checked at destination, nor individual chunks right order is not verified. These should be addressed in further improvements.*

```
>gs
(lat)<2.3
(lon)<4.5
Gps: (2.3, 4.5)
```
Sets localisation coordinates; useful where no Pytrack is used.

```
>gg
Gps: (2.2, 1.1)
```
Shows latest GPS coordinates.

```
> rst
1
```
Resets the Pymesh parameters saved in NVM, and resets the Node.

```
> rb
```
Resets BLE RPC buffer.

## LoRa MAC address Set/Read

### Set LoRa Mac
```python
fo = open("/flash/sys/lpwan.mac", "wb")
mac_write=bytes([0,0,0,0,0,0,0,20])
fo.write(mac_write)
fo.close()
```

### Read LoRa MAC address
```python
>>> from network import LoRa
>>> lora = LoRa(mode=LoRa.LORA, region=LoRa.EU868, frequency = 863000000, bandwidth=LoRa.BW_125KHZ, sf=7)
>>> import ubinascii
>>> ubinascii.hexlify(lora.mac())
b'0000000000000006'
```
