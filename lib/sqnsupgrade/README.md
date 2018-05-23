# Firmware upgrade tool for the Sequans Monarch SQN3330

## Description

These libraries contain the necesary code to upgrade the firmware of the cellular radio found in the FiPy, GPy and G01.
The process involves streaming the firmware file from the ESP32 to the SQN3330. Currently, the file has to be stored in a
micro SD card first so that the ESP32 can access it easily. In the next few days we will add support for streaming the file via the updater tool as well.

## Usage

### Using a SD card

Download the firmware file via the link and the bottom. Place the firmware in a FAT32 formatted microSD card. Then insert the SD card in one in a expansion board, pytrack or pysense. Power-up the system, upload the libraries to the module and after that run the piece of code below:

```python
import sqnsupgrade
sqnsupgrade.run(path_to_firmware, 921600)   # path_to_firmware example: '/sd/FIPY_NB1_35351.dup'
```

### Streaming the firmware on a PC via the serial port used for the REPL

Download the firmware file via the link and the bottom. Run the **uartmirror.py** script on the device. This will alow the PC to control the cellular modem directly bypassing the ESP32. Then open a Python 3 terminal on the PC (make sure Pyserial is installed) and run:

```python
import sqnsupgrade
sqnsupgrade.run(path_to_firmware, 921600, port=serial_port) # path_to_firmware example: '/sd/FIPY_NB1_35351.dup, serial port example: '/dev/tty.usbmodemPy2e5401'
```

The whole process can take between 2 and 3 minutes and at some points it will seem to stall, this is normal, just have a little patience.

You should see an output like this:

```bash
<<< Welcome to the SQN3330 firmware updater >>>
Entering recovery mode
Resetting.

Starting STP (DO NOT DISCONNECT POWER!!!)
STP started
Session opened: version 1, max transfer 8192 bytes
Sending 4560505 bytes: [########################################] 100%
Code download done, returning to user mode
Resetting (DO NOT DISCONNECT POWER!!!).
.........
Deploying the upgrade (DO NOT DISCONNECT POWER!!!)...
Resetting (DO NOT DISCONNECT POWER!!!)..
...
Upgrade completed!
Here is the current firmware version:
UE6.0.0.0-ER7
LR6.0.0.0-35351
OK
```

## IMPORTANT:

DO NOT disconnect power while the upgrade process is taking place, wait for it to finish!.

If the module get's stuck in here:

```bash
Sending 4560505 bytes: [##                                      ]   6%
```

For more than 1 minute while upgrading to the NB-IoT firmware, you can cycle power and retry. In this case it is safe.

The latest Cat-M1 firmware is the following:

```bash
UE5.0.0.0c
LR5.1.1.0-33988
```

And this is the latest NB-IoT firmware:

```bash
UE6.0.0.0-ER7
LR6.0.0.0-35351
```

## Current NB-IoT limitations

At the moment the NB-IoT firmware supplied by Sequans only support Ericsson base stations configured for In-Band mode. Standalone and guard-band modes will be supported in a later release. Support for Huawei base stations is also limmited and only lab testing with Huawei eNodeB is recommended at the moment. Full support for Huawei is planned for early Q2 2018.

# NB-IoT usage:

for example with Vodafone:

```python
from network import LTE

lte = LTE()
lte.send_at_cmd('AT+CFUN=0')
lte.send_at_cmd('AT!="clearscanconfig"')
lte.send_at_cmd('AT!="addscanfreq band=20 dl-earfcn=6300"')
lte.send_at_cmd('AT!="zsp0:npc 1"')
lte.send_at_cmd('AT+CGDCONT=1,"IP","nb.inetd.gdsp"')
lte.send_at_cmd('AT+CFUN=1')

while not lte.isattached():
    pass

lte.connect()
while not lte.isconnected():
    pass

# now use socket as usual...
```

## SQN3330 Firmware download link

https://software.pycom.io/downloads/sequans.html
