<p align="center"><img src ="https://github.com/pycom/pycom-libraries/blob/master/img/logo.png" width="300"></p>

# Pybytes Examples

Please note that these examples only work when using the `pybytes` firmware.

# Pytrack, Pysense, Pyscan
- To run pytrack on individuals module you will need to create one pybytes_config.json file on root which usually contains data related to device e.g Network preferance, device id, server, username, password etc.

- You will needs to upload all the files to module in order to get data on pybytes dashboard.

Note: Note: For using Pyscan, you need to upload either MFRC630.mpy or MFRC630.py.
It is always recommended to use MFRC630.mpy as it takes less space on your module.

- Pytrack:
GPS coordinate and Acceleration would give result in tuples.

- Pysense:
Humidity and temperature output would be in float32.
Light sensor output would be in tuples.

- Pyscan:
Light sensor and Acceleration would give output in tuples.
