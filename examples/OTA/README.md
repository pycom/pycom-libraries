Overview
--------

This directory contains a example implementation of over the air (OTA)
firmware updates. This consists of two components:
  - A server that serves the update files and generates update "manifests"
  - A library that allows a Pycom module perform updates from the server

This directory is laid out such that the update sever can directly run from it.
For a detailed description of how the server expect the directory to be structured please read the comment at the top of `OTA_server.py`.

Setup
-----
To start the server simply run the `OTA_server.py` script using python 3. This
will run a HTTP server on port 8000 (this can be changed in the code if
necessary).

In this project you will find two directories named `1.0.0` and `1.0.1`. These
are both working examples of the OTA procedure, the only difference being the
colour of the on-board LED so that a successful update can be demonstrated. You
should upload version `1.0.0` to the module first and then via the OTA update
procedure it will update to version `1.0.1`.

In this example the OTA procedure is trigger via LoRaWAN downlink message. In
order to use these examples you will need to enter your own `app_eui` and
`app_key`. As well as this you will need to edit `config.py` to add your WiFi
SSID, password and the address of the update server. Ensure you make these changes in both `1.0.0` and `1.0.1` or the code will stop working after the
OTA update.

The OTA library can be found in either `1.0.0\lib\OTA.py` or
`1.0.1\lib\OTA.py`.

For a detailed explanation of how the server works please look in
`OTA_server.py`. The comment at the top of the file explains how it works in
detail.
