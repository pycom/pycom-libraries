import time
import machine
from onewire import DS18X20
from onewire import OneWire

import usocket as socket

publicKey = 'SPARKFUNCHANNELPUBLICKEY'
privateKey = 'SPARKFUNCAHNNELPRIVATEKEY'


#DS18B20 data line connected to pin P10
ow = OneWire(machine.Pin('P10'))
temp = DS18X20(ow)

while True:
    temp.start_conversion()
    time.sleep(1)
    tempValue = temp.read_temp_async()/100.0
    u = 'POST /input/%s?private_key=%s&temp=%f HTTP/1.0\n\n'%( publicKey, privateKey, tempValue)
    
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    ai = socket.getaddrinfo("data.sparkfun.com", 80)
    addr = ai[0][4]
    s.connect(addr)
    s.sendall(u)
    status = s.recv(4096)
    s.close()
    print('POST temp=%f'%tempValue)
    time.sleep(10)
