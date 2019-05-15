<p align="center"><img src ="https://github.com/pycom/pycom-libraries/blob/master/img/logo.png" width="300"></p>

# Google Cloud Iot Core MQTT connection library

### requirement

Pycom Firmware >= 1.20.0.rc11

You will need to setup a Google IoT core registry as described here: https://cloud.google.com/iot/docs/quickstart#create_a_device_registry

During the activation please collect the following informations: 'project_id',
 'cloud_region' and 'registry_id'.

### usage

- create a device registry:
https://cloud.google.com/iot/docs/quickstart#create_a_device_registry
- generate a key using the provided tool genkey.sh and add it to the platform
- add the public key to Google IoT Core :
https://cloud.google.com/iot/docs/quickstart#add_a_device_to_the_registry
- copy config.example.py to config.py and edit the variable
- upload the project using pymakr
