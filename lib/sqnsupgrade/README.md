# Firmware upgrade tool for the Sequans Monarch SQN3330

## Description

These libraries contain the necessary code to upgrade the firmware of the cellular radio found in the FiPy, GPy and G01.
The process involves streaming the firmware file from the ESP32 to the SQN3330. Currently, the file has to be stored in a
Micro SD card first so that the ESP32 can access it easily. In the next few days we will add support for streaming the file via the updater tool as well.

## Usage

### Using a SD card

Download the firmware file via the link and the bottom. Place the firmware in a FAT32 formatted microSD card. Then insert the SD card in one in a expansion board, Pytrack or Pysense. Power-up the system, upload the libraries to the module and after that run the piece of code below:

```python
import sqnsupgrade
sqnsupgrade.run(path_to_firmware)   # path_to_firmware example: '/sd/FIPY_NB1_35351.dup'
```

### Streaming the firmware on a PC via the serial port used for the REPL

To improve the stability of the serial connection, please first update the GPy / FiPy firmware using the following files:

GPy: https://software.pycom.io/downloads/GPy-1.18.0.r1.tar.gz

FiPy: https://software.pycom.io/downloads/FiPy-1.18.0.r1.tar.gz

Use the latest version of the Pycom Firmware Updater and choose Flash from local file in the Communication Window to flash this special firmware.

Download the firmware file via the link at the bottom. Run the **uartmirror.py** script on the device. This will allow the PC to control the cellular modem directly bypassing the ESP32. Then open a Python 3 terminal on the PC (make sure Pyserial is installed) and run:

```python
import sqnsupgrade
sqnsupgrade.run(path_to_firmware, 921600, port=serial_port) # path_to_firmware example: '/sd/FIPY_NB1_35351.dup, serial port example: '/dev/tty.usbmodemPy2e5401'
```

The GPy & FiPy firmware above is pretty much identical to the latest firmware except that is has a much larger UART buffer. If you have any issues with this firmware, please email support@pycom.io to let us know.


### Upgrade process

The whole process can take several minutes and at several points it will seem to stall, this is normal, just have a little patience.

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
UE5.0.0.0d
LR5.1.1.0-36417
```

And this is the latest NB-IoT firmware:

```bash
UE6.0.0.0
LR6.0.0.0-37781
```

If you get the message AT+SMSWBOOT=3,0 failed!, please try adding the resume=True option, e.g. sqnsupgrade.run(path_to_firmware, resume=True)
This may not work in all situations and we are working closely with Sequans to find solutions. 

## Current NB-IoT limitations (this is outdated and will be updated soon)

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
